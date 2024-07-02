import os
import re
import yaml
from datetime import datetime
from typing import Dict, Tuple

AFFILIATES_DIR = 'affiliates-wins(promotion)'
README_PATH = 'README.md'
DATE_FORMAT = '%Y-%m-%d'

def get_affiliates_and_latest_submissions() -> Dict[str, Tuple[datetime, int]]:
    affiliates = {}
    for root, _, files in os.walk(AFFILIATES_DIR):
        for file in files:
            if file.endswith('_submission.md'):
                affiliate = os.path.basename(os.path.dirname(os.path.join(root, file)))
                file_path = os.path.join(root, file)
                date, referral_count = extract_submission_info(file_path)
                
                if affiliate not in affiliates or date > affiliates[affiliate][0]:
                    affiliates[affiliate] = (date, referral_count)
    return affiliates

def extract_submission_info(file_path: str) -> Tuple[datetime, int]:
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            frontmatter = yaml.safe_load(content.split('---')[1])
            date = datetime.strptime(frontmatter['date'], DATE_FORMAT)
            referral_count = frontmatter.get('referral_count', 0)
        return date, referral_count
    except (IOError, yaml.YAMLError, KeyError, IndexError) as e:
        print(f"Error processing {file_path}: {str(e)}")
        return datetime.min, 0

def update_main_readme(affiliates: Dict[str, Tuple[datetime, int]]) -> None:
    try:
        with open(README_PATH, 'r') as f:
            content = f.read()

        start_marker = "<!-- AFFILIATE LIST START -->"
        end_marker = "<!-- AFFILIATE LIST END -->"
        pattern = re.compile(f'{start_marker}.*?{end_marker}', re.DOTALL)

        new_content = f"{start_marker}\n\n"
        new_content += "| Affiliate | Latest Submission | Total Referrals |\n"
        new_content += "|-----------|--------------------|-----------------|\n"
        for affiliate, (date, referral_count) in sorted(affiliates.items()):
            new_content += f"| {affiliate} | {date.strftime(DATE_FORMAT)} | {referral_count} |\n"
        new_content += f"\n{end_marker}"

        updated_content = pattern.sub(new_content, content)

        with open(README_PATH, 'w') as f:
            f.write(updated_content)
        
        print("Main README.md updated successfully.")
    except IOError as e:
        print(f"Error updating README: {str(e)}")

def main() -> None:
    try:
        affiliates = get_affiliates_and_latest_submissions()
        update_main_readme(affiliates)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
