#!/usr/bin/env python3
"""
PDF Prompt Injection Scanner
-----------------------------
Extracts text from a PDF file, splits it into manageable chunks,
and runs each chunk through the 9-layer GuardrailPipeline to detect
any embedded prompt injection attacks.

Usage:
    python pdf_scanner.py <path_to_pdf> [--chunk-size 500] [--overlap 50] [--verbose]

Returns a final verdict:
    🔴 MALICIOUS  - One or more INJECTION chunks detected
    🟡 SUSPICIOUS - Suspicious patterns found, no hard injection
    🟢 SAFE       - All chunks passed cleanly
"""

import sys
import io

# Force UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import os
import re
import json
import argparse
import time
from dataclasses import dataclass, asdict
from typing import List, Tuple

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompt_injection_detector.pipeline import GuardrailPipeline, PipelineResult


# ─── PDF Text Extraction ──────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int]:
    """
    Extract all text from a PDF using PyMuPDF (fitz).
    Returns (full_text, page_count).
    Raises ImportError if PyMuPDF is not installed.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF scanning.\n"
            "Install it with:  pip install pymupdf"
        )

    doc = fitz.open(pdf_path)
    page_count = len(doc)
    pages_text = []

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        if page_text.strip():
            pages_text.append(f"[Page {page_num}]\n{page_text}")

    doc.close()
    return "\n\n".join(pages_text), page_count


# ─── Text Chunker ─────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Tuple[str, int]]:
    """
    Split text into overlapping word-level chunks.
    Returns a list of (chunk_text, start_word_index) tuples.

    Args:
        text:       Full document text.
        chunk_size: Max number of words per chunk.
        overlap:    Number of words to overlap between chunks (context continuity).
    """
    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append((chunk, start))
        if end == len(words):
            break
        start += chunk_size - overlap  # slide with overlap

    return chunks


# ─── Result Aggregation ───────────────────────────────────────────────────────

@dataclass
class ChunkResult:
    chunk_index: int
    start_word: int
    preview: str          # first 120 chars of chunk
    status: str           # ALLOWED / BLOCKED / SANITIZED / REWRITTEN
    verdict: str          # SAFE / SUSPICIOUS / INJECTION
    confidence: float
    reason: str
    layer_triggered: str
    latency_ms: float


@dataclass
class PDFScanReport:
    pdf_path: str
    page_count: int
    total_chunks: int
    final_verdict: str    # MALICIOUS / SUSPICIOUS / SAFE
    overall_confidence: float
    injection_chunks: int
    suspicious_chunks: int
    safe_chunks: int
    scan_time_sec: float
    chunk_results: List[ChunkResult]

    def summary(self) -> str:
        icon = {"MALICIOUS": "[MALICIOUS]", "SUSPICIOUS": "[SUSPICIOUS]", "SAFE": "[SAFE]"}.get(self.final_verdict, "[?]")
        lines = [
            "",
            "=" * 65,
            f"  PDF PROMPT INJECTION SCAN REPORT",
            "=" * 65,
            f"  File         : {os.path.basename(self.pdf_path)}",
            f"  Pages        : {self.page_count}",
            f"  Chunks       : {self.total_chunks}",
            f"  Scan Time    : {self.scan_time_sec:.2f}s",
            "-" * 65,
            f"  Final Verdict: {icon} {self.final_verdict}",
            f"  Confidence   : {self.overall_confidence:.1%}",
            f"  [!!] Injection : {self.injection_chunks} chunk(s)",
            f"  [??] Suspicious: {self.suspicious_chunks} chunk(s)",
            f"  [OK] Safe      : {self.safe_chunks} chunk(s)",
            "=" * 65,
        ]
        return "\n".join(lines)

    def flagged_chunks_summary(self) -> str:
        flagged = [c for c in self.chunk_results if c.verdict != "SAFE"]
        if not flagged:
            return "  No flagged chunks found."
        lines = ["\n  FLAGGED CHUNKS:"]
        for c in flagged:
            icon = "[!!]" if c.verdict == "INJECTION" else "[??]"
            lines.append(f"\n  {icon} Chunk #{c.chunk_index + 1} | Verdict: {c.verdict} | Confidence: {c.confidence:.1%}")
            lines.append(f"    Layer    : {c.layer_triggered}")
            lines.append(f"    Reason   : {c.reason}")
            lines.append(f"    Preview  : \"{c.preview}...\"")
        return "\n".join(lines)


# ─── Core Scanner ─────────────────────────────────────────────────────────────

def scan_pdf(
    pdf_path: str,
    chunk_size: int = 500,
    overlap: int = 50,
    verbose: bool = False,
    batch_size: int = 8,
) -> PDFScanReport:
    """
    Full PDF scan pipeline:
    1. Extract text from PDF
    2. Chunk the text
    3. Run all chunks through GuardrailPipeline (batched)
    4. Aggregate and return a PDFScanReport
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    scan_start = time.time()

    # Step 1: Extract
    print(f"\n[PDF] Extracting text from: {os.path.basename(pdf_path)}")
    full_text, page_count = extract_text_from_pdf(pdf_path)

    if not full_text.strip():
        raise ValueError("PDF appears to be empty or contains only images (no extractable text).")

    word_count = len(full_text.split())
    print(f"   [OK] Extracted {word_count:,} words from {page_count} page(s)")

    # Step 2: Chunk
    chunks = chunk_text(full_text, chunk_size=chunk_size, overlap=overlap)
    print(f"   [OK] Split into {len(chunks)} chunk(s) (chunk_size={chunk_size}, overlap={overlap})")

    # Step 3: Initialize pipeline (only once)
    print("\n[INIT] Initializing GuardrailPipeline...")
    pipeline = GuardrailPipeline()

    # Step 4: Run in batches
    print(f"\n[SCAN] Scanning {len(chunks)} chunk(s) in batches of {batch_size}...")
    all_pipeline_results: List[PipelineResult] = []

    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start: batch_start + batch_size]
        batch_texts = [c[0] for c in batch]
        results = pipeline.run_batch(batch_texts)
        all_pipeline_results.extend(results)

        if verbose:
            for j, res in enumerate(results):
                ci = batch_start + j
                icon = "[!!]" if res.verdict == "INJECTION" else ("[??]" if res.verdict == "SUSPICIOUS" else "[OK]")
                print(f"   Chunk {ci + 1:>3}/{len(chunks)} {icon} {res.verdict:<12} conf={res.confidence:.2f}  [{res.layer_triggered}]")

    # Step 5: Aggregate
    chunk_results = []
    injection_count = 0
    suspicious_count = 0
    safe_count = 0
    max_injection_conf = 0.0
    max_suspicious_conf = 0.0

    for i, (res, (chunk_text_val, start_word)) in enumerate(zip(all_pipeline_results, chunks)):
        cr = ChunkResult(
            chunk_index=i,
            start_word=start_word,
            preview=chunk_text_val[:120].replace("\n", " "),
            status=res.status,
            verdict=res.verdict,
            confidence=res.confidence,
            reason=res.reason,
            layer_triggered=res.layer_triggered,
            latency_ms=res.latency * 1000,
        )
        chunk_results.append(cr)

        if res.verdict == "INJECTION":
            injection_count += 1
            max_injection_conf = max(max_injection_conf, res.confidence)
        elif res.verdict == "SUSPICIOUS":
            suspicious_count += 1
            max_suspicious_conf = max(max_suspicious_conf, res.confidence)
        else:
            safe_count += 1

    # Final verdict logic
    if injection_count > 0:
        final_verdict = "MALICIOUS"
        overall_confidence = max_injection_conf
    elif suspicious_count > 0:
        final_verdict = "SUSPICIOUS"
        overall_confidence = max_suspicious_conf
    else:
        final_verdict = "SAFE"
        # Confidence = average safe confidence across chunks
        overall_confidence = sum(
            c.confidence for c in chunk_results if c.verdict == "SAFE"
        ) / max(1, safe_count)

    scan_time = time.time() - scan_start

    return PDFScanReport(
        pdf_path=pdf_path,
        page_count=page_count,
        total_chunks=len(chunks),
        final_verdict=final_verdict,
        overall_confidence=overall_confidence,
        injection_chunks=injection_count,
        suspicious_chunks=suspicious_count,
        safe_chunks=safe_count,
        scan_time_sec=scan_time,
        chunk_results=chunk_results,
    )


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scan a PDF for embedded prompt injection attacks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdf", help="Path to the PDF file to scan")
    parser.add_argument(
        "--chunk-size", type=int, default=500,
        help="Words per chunk (default: 500)"
    )
    parser.add_argument(
        "--overlap", type=int, default=50,
        help="Word overlap between chunks (default: 50)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Chunks per inference batch (default: 8)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show per-chunk results during scan"
    )
    parser.add_argument(
        "--json-out", type=str, default=None,
        help="Optional path to save the full report as JSON"
    )

    args = parser.parse_args()

    try:
        report = scan_pdf(
            pdf_path=args.pdf,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            verbose=args.verbose,
            batch_size=args.batch_size,
        )

        # Print summary
        print(report.summary())
        print(report.flagged_chunks_summary())
        print()

        # Optionally save JSON
        if args.json_out:
            report_dict = asdict(report)
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2)
            print(f"\n📝 Full report saved to: {args.json_out}")

        # Exit code: 0=safe, 1=suspicious, 2=malicious
        exit_codes = {"SAFE": 0, "SUSPICIOUS": 1, "MALICIOUS": 2}
        sys.exit(exit_codes.get(report.final_verdict, 3))

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(10)
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}", file=sys.stderr)
        sys.exit(11)
    except ValueError as e:
        print(f"\n⚠️  Warning: {e}", file=sys.stderr)
        sys.exit(12)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(99)


if __name__ == "__main__":
    main()
