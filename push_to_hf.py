import os
from huggingface_hub import HfApi

def upload_model():
    # Set your repo ID here
    repo_id = "raghavendrak8162/deberta-v3-prompt-injector"
    
    print(f"Preparing to upload v3_massive_model to: {repo_id}")
    
    api = HfApi()
    
    from huggingface_hub import login
    # Check if we are logged in
    try:
        user_info = api.whoami()
        print(f"Authenticated as: {user_info['name']}")
    except Exception as e:
        print("\n--- Hugging Face Login Required ---")
        print("Please get your Write Access Token from: https://huggingface.co/settings/tokens")
        token = input("Paste your token here and press Enter: ").strip()
        if not token:
            print("No token provided. Exiting.")
            return
        
        try:
            login(token=token)
            user_info = api.whoami()
            print(f"Successfully authenticated as: {user_info['name']}")
        except Exception as login_err:
            print(f"Login failed: {login_err}")
            return

    print("\nUploading model files... This might take a few minutes depending on your internet speed.")
    try:
        # Upload the model directory
        api.upload_folder(
            folder_path="v3_massive_model",
            repo_id=repo_id,
            commit_message="Update GuardRail Massive ML Model"
        )
        print("✅ Model uploaded successfully!")
        
        # Optionally upload the README and Project Report
        print("Uploading documentation...")
        if os.path.exists("Project_Report.md"):
            api.upload_file(
                path_or_fileobj="Project_Report.md",
                path_in_repo="Project_Report.md",
                repo_id=repo_id,
                commit_message="Add Project Report"
            )
        if os.path.exists("README.md"):
            api.upload_file(
                path_or_fileobj="README.md",
                path_in_repo="README.md",
                repo_id=repo_id,
                commit_message="Update README"
            )
        print("✅ Documentation uploaded successfully!")
        print(f"\nYour files are now live at: https://huggingface.co/{repo_id}")
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")

if __name__ == "__main__":
    upload_model()
