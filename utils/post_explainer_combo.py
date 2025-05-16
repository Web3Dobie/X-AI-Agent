from content.explainer import post_dobie_explainer_thread
from content.explainer_writer import generate_substack_explainer

def post_explainer_combo():
    # Step 1: Post the 3-part X thread
    print("📢 Posting explainer thread on X...")
    post_dobie_explainer_thread()

    # Step 2: Generate the Substack article and log it
    print("📝 Generating Substack article...")
    result = generate_substack_explainer()
    if result:
        print(f"✅ Substack article saved to: {result['filename']}")
    else:
        print("❌ Substack article generation failed.")

