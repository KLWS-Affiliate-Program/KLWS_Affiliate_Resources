import os
import re
import yaml
from typing import List, NamedTuple

# Define paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APRL_DIR = os.path.join(REPO_ROOT, 'Promotion_Logs', 'affiliate_logs')
SALES_DIR = os.path.join(REPO_ROOT, 'Sales_Logs', 'affiliate_logs')
MAIN_README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'README.md')

class Submission(NamedTuple):
    affiliate_tag: str
    referral_count: int
    agreed_price: int

def parse_aprl_submission(file_path: str) -> Submission:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    frontmatter = yaml.safe_load(content.split('---')[1])
    return Submission(affiliate_tag=frontmatter.get('affiliate_tag', ''), referral_count=frontmatter.get('referral_count', 0), agreed_price=0)

def parse_sales_submission(file_path: str) -> Submission:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    frontmatter = yaml.safe_load(content.split('---')[1])
    agreed_price = int(frontmatter.get('agreed_price', '0').replace('₦', '').replace(',', ''))
    return Submission(affiliate_tag=frontmatter.get('affiliate_tag', ''), referral_count=0, agreed_price=agreed_price)

def get_submissions(directory: str, parse_func) -> List[Submission]:
    submissions = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('_submission.md') or file.endswith('_sale_submission.md'):
                submissions.append(parse_func(os.path.join(root, file)))
    return submissions

def generate_quick_stats() -> str:
    aprl_submissions = get_submissions(APRL_DIR, parse_aprl_submission)
    sales_submissions = get_submissions(SALES_DIR, parse_sales_submission)
    
    total_referrals = sum(s.referral_count for s in aprl_submissions)
    
    # Count unique affiliates
    unique_affiliates = len(set(s.affiliate_tag for s in aprl_submissions))
    
    avg_referrals = round(total_referrals / unique_affiliates) if unique_affiliates > 0 else 0
    
    total_sales_logs = len(sales_submissions)
    total_aprl_logs = len(aprl_submissions)
    total_sales_amount = sum(s.agreed_price for s in sales_submissions)
    avg_sale_price = round(total_sales_amount / total_sales_logs) if total_sales_logs > 0 else 0

    stats = f"""
- Total Affiliate Logs: {total_aprl_logs} (Promotion Logs), {total_sales_logs} (Sale Logs)

### Pricing Insights

- On average, our affiliates price the service at ₦{avg_sale_price:,}

### Promotion Insights

- Total Referrals: {total_referrals}
- Average Referrals per Affiliate: {avg_referrals}
"""
    return stats

def update_readme_section(content: str, start_marker: str, end_marker: str, new_content: str) -> str:
    pattern = fr"({re.escape(start_marker)}).*?({re.escape(end_marker)})"
    replacement = f"\\1\n{new_content}\n\\2"
    return re.sub(pattern, replacement, content, flags=re.DOTALL)

def main():
    # Read the current README content
    with open(MAIN_README_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generate and update the Quick Stats section
    quick_stats = generate_quick_stats()
    updated_content = update_readme_section(content, "## Quick Stats", "## How to Use", quick_stats)

    # Write the updated content back to the README
    with open(MAIN_README_PATH, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print("Main README updated successfully!")

if __name__ == "__main__":
    main()