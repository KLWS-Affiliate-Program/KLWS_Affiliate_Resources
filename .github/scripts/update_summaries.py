import os
import re
import yaml
from datetime import datetime, date
from typing import Dict, List, NamedTuple
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# Define constants for commonly used paths and formats
AFFILIATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'affiliates-wins')
README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'README.md')
DATE_FORMAT = '%Y-%m-%d'

# Define a structure for submission data
class Submission(NamedTuple):
    date: datetime
    file_path: str
    referral_count: int
    strategies: List[str]
    referral_types: List[str]

def parse_submission_file(file_path: str) -> Submission:
    """
    Read a submission file and extract its data.
    Returns a Submission object or a default one if there's an error.
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        frontmatter = yaml.safe_load(content.split('---')[1])
        
        # Ensure the date is a string or a datetime object
        date_value = frontmatter['date']
        if isinstance(date_value, datetime):
            date_str = date_value.strftime(DATE_FORMAT)
        elif isinstance(date_value, date):
            date_str = date_value.strftime(DATE_FORMAT)
        else:
            date_str = date_value

        return Submission(
            date=datetime.strptime(date_str, DATE_FORMAT),
            file_path=file_path,
            referral_count=frontmatter.get('referral_count', 0),
            strategies=frontmatter.get('strategies', []),
            referral_types=frontmatter.get('referral_types', [])
        )
    except (IOError, yaml.YAMLError, KeyError, IndexError, ValueError) as e:
        return Submission(datetime.min, file_path, 0, [], [])

def get_affiliates_and_submissions() -> Dict[str, List[Submission]]:
    affiliates = {}
    with ThreadPoolExecutor() as executor:
        future_to_file = {
            executor.submit(parse_submission_file, os.path.join(root, file)): (os.path.basename(root), os.path.join(root, file))
            for root, _, files in os.walk(AFFILIATES_DIR)
            for file in files if file.endswith('_submission.md')
        }
        
        for future in as_completed(future_to_file):
            affiliate, file_path = future_to_file[future]
            submission = future.result()
            if submission.referral_count > 0:  # Only add valid submissions
                if affiliate not in affiliates:
                    affiliates[affiliate] = []
                affiliates[affiliate].append(submission)
    
    return affiliates

def update_main_readme(affiliates: Dict[str, List[Submission]]) -> None:
    """
    Update the main README with a table of affiliates, their latest submissions, and total referrals.
    """
    try:
        with open(README_PATH, 'r') as f:
            content = f.read()
        
        new_content = "<!-- AFFILIATE LIST START -->\n\n"
        new_content += "| Affiliate | Latest Submission | Total Referrals |\n"
        new_content += "|-----------|--------------------|-----------------|\n"
        
        for affiliate, submissions in sorted(affiliates.items()):
            latest_submission = max(submissions, key=lambda x: x.date)
            total_referrals = sum(submission.referral_count for submission in submissions)
            new_content += f"| {affiliate} | {latest_submission.date.strftime(DATE_FORMAT)} | {total_referrals} |\n"
        
        new_content += "\n<!-- AFFILIATE LIST END -->"
        
        content = re.sub(
            r'<!-- AFFILIATE LIST START -->.*?<!-- AFFILIATE LIST END -->',
            new_content,
            content,
            flags=re.DOTALL
        )
        
        with open(README_PATH, 'w') as f:
            f.write(content)
        
    except IOError as e:
        print(f"Error updating README: {str(e)}")

def update_affiliate_readme(affiliate: str, submissions: List[Submission]) -> None:
    """
    Create or update an individual affiliate's README with their submissions and stats.
    """
    readme_path = os.path.join(AFFILIATES_DIR, affiliate, 'README.md')
    content = f"# {affiliate}'s Submissions\n\n"
    content += "| Date | Referral Count | Strategies | Referral Types |\n"
    content += "|------|----------------|------------|----------------|\n"

    total_referrals = 0
    all_strategies = []
    all_referral_types = []

    for submission in sorted(submissions, key=lambda x: x.date, reverse=True):
        content += (f"| {submission.date.strftime(DATE_FORMAT)} | {submission.referral_count} | "
                    f"{', '.join(submission.strategies)} | {', '.join(submission.referral_types)} |\n")
        total_referrals += submission.referral_count
        all_strategies.extend(submission.strategies)
        all_referral_types.extend(submission.referral_types)

    content += f"\n## Key Stats\n"
    content += f"- Total Submissions: {len(submissions)}\n"
    content += f"- Total Referrals: {total_referrals}\n"
    content += f"- Top Strategy: {Counter(all_strategies).most_common(1)[0][0] if all_strategies else 'N/A'}\n"
    content += f"- Most Common Referral Type: {Counter(all_referral_types).most_common(1)[0][0] if all_referral_types else 'N/A'}\n"

    os.makedirs(os.path.dirname(readme_path), exist_ok=True)
    with open(readme_path, 'w') as f:
        f.write(content)

def generate_tag_cloud(affiliates: Dict[str, List[Submission]]) -> None:
    """
    Generate a tag cloud from all strategies and referral types and add it to the main README.
    """
    all_tags = [tag for submissions in affiliates.values() for submission in submissions for tag in (submission.strategies + submission.referral_types)]
    
    tag_counts = Counter(all_tags)
    tag_cloud = ' '.join(f'{tag}({count})' for tag, count in tag_counts.most_common(20))

    with open(README_PATH, 'r') as f:
        content = f.read()

    new_content = f"<!-- TAG CLOUD START -->\n\n{tag_cloud}\n\n<!-- TAG CLOUD END -->"
    
    content = re.sub(
        r'<!-- TAG CLOUD START -->.*?<!-- TAG CLOUD END -->',
        new_content,
        content,
        flags=re.DOTALL
    )

    with open(README_PATH, 'w') as f:
        f.write(content)

def main() -> None:
    """
    Main function to orchestrate the README update process.
    """
    try:
        affiliates = get_affiliates_and_submissions()
        update_main_readme(affiliates)
        
        with ThreadPoolExecutor() as executor:
            executor.map(lambda x: update_affiliate_readme(*x), affiliates.items())
        
        generate_tag_cloud(affiliates)
        
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
