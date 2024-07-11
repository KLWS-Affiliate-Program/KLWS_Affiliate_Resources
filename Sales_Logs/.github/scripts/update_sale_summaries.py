import os
import re
import yaml
from datetime import datetime
from typing import Dict, List, NamedTuple
from collections import Counter

# Define constants for commonly used paths and formats
AFFILIATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'affiliate_logs')
README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'README.md')
DATE_FORMAT = '%Y-%m-%d-%H%M%S'

# Define a structure for submission data
class Submission(NamedTuple):
    date: datetime
    file_path: str
    affiliate_tag: str
    agreed_price: int
    client_type: str
    sale_duration: str
    key_approach: str
    what_went_well: str
    future_improvements: str
    advice_for_others: str

def parse_submission_file(file_path: str) -> Submission:
    """Parse a submission file and extract its data into a Submission object."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            parts = f.read().split('---', 2)
        
        frontmatter = yaml.safe_load(parts[1])
        sections = {section.split('\n')[0].strip(): '\n'.join(section.split('\n')[1:]).strip() 
                    for section in re.split(r'##\s+', parts[2]) if section.strip()}

        date_value = frontmatter['date']
        submission_date = (datetime.strptime(date_value, DATE_FORMAT) if isinstance(date_value, str)
                           else datetime.combine(date_value, datetime.min.time()))

        agreed_price = int(frontmatter['agreed_price'].replace('₦', '').replace(',', ''))

        return Submission(
            date=submission_date,
            file_path=file_path,
            affiliate_tag=frontmatter['affiliate_tag'],
            agreed_price=agreed_price,
            client_type=frontmatter['client_type'],
            sale_duration=frontmatter['sale_duration'],
            key_approach=sections.get('Key Approach', ''),
            what_went_well=sections.get('What Went Well', ''),
            future_improvements=sections.get('Future Improvements', ''),
            advice_for_others=sections.get('Advice for Other Affiliates', '')
        )
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
        return Submission(datetime.min, file_path, '', 0, '', '', '', '', '', '')

def get_affiliates_and_submissions() -> Dict[str, List[Submission]]:
    """Collect all valid submissions for each affiliate."""
    affiliates = {}
    for root, _, files in os.walk(AFFILIATES_DIR):
        for file in files:
            if file.endswith('.md') and not file.endswith('README.md'):
                submission = parse_submission_file(os.path.join(root, file))
                if submission.agreed_price > 0:  # Only add valid submissions
                    affiliates.setdefault(submission.affiliate_tag, []).append(submission)
    return affiliates

def update_readme_section(content: str, start_marker: str, end_marker: str, new_content: str) -> str:
    """Update a specific section in the README."""
    pattern = fr"({re.escape(start_marker)}).*?({re.escape(end_marker)})"
    replacement = f"\\1\n{new_content}\n\\2"
    return re.sub(pattern, replacement, content, flags=re.DOTALL)

def generate_affiliate_table(affiliates: Dict[str, List[Submission]]) -> str:
    """Generate the affiliate table content."""
    table = "| Affiliate | Latest Submission | Total Sales |\n"
    table += "|-----------|--------------------|--------------|\n"
    for affiliate, submissions in sorted(affiliates.items(), key=lambda x: sum(s.agreed_price for s in x[1]), reverse=True):
        latest_submission = max(submissions, key=lambda x: x.date)
        total_sales = sum(s.agreed_price for s in submissions)
        
        affiliate_dir = os.path.relpath(os.path.join(AFFILIATES_DIR, affiliate.replace(" - ", "_")), start=os.path.dirname(README_PATH)).replace('\\', '/')
        submission_path = os.path.relpath(latest_submission.file_path, start=os.path.dirname(README_PATH)).replace('\\', '/')
        
        table += f"| [{affiliate}]({affiliate_dir}) | [{latest_submission.date.strftime(DATE_FORMAT)}]({submission_path}) | ₦{total_sales:,} |\n"
    
    return table

def get_top_items_by_value(submissions: List[Submission], attribute: str, n: int = 8) -> str:
    """Get top n items based on agreed price."""
    items = {}
    for submission in submissions:
        item = getattr(submission, attribute)
        if item:
            items[item] = items.get(item, 0) + submission.agreed_price
    
    return "\n".join(f"- {item} (₦{value:,})" for item, value in sorted(items.items(), key=lambda x: x[1], reverse=True)[:n])

def get_top_items_by_occurrences(submissions: List[Submission], attribute: str, n: int = 8) -> str:
    """Get top n items based on occurrences."""
    items = Counter(getattr(submission, attribute) for submission in submissions if getattr(submission, attribute))
    return "\n".join(f"- {item} ({count})" for item, count in items.most_common(n))

def generate_pricing_insights(submissions: List[Submission]) -> str:
    """Generate pricing insights."""
    if not submissions:
        return "No data available."
    
    avg_price = sum(s.agreed_price for s in submissions) // len(submissions)
    return f"On average, our affiliates price the service at ₦{avg_price:,}."

def generate_program_stats(affiliates: Dict[str, List[Submission]]) -> str:
    """Generate overall program statistics."""
    total_affiliates = len(affiliates)
    total_submissions = sum(len(submissions) for submissions in affiliates.values())
    return f"- Affiliates with Logs: {total_affiliates}\n- Total Submissions: {total_submissions}"

def update_main_readme(affiliates: Dict[str, List[Submission]]) -> None:
    """Update the main README with all sections."""
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = update_readme_section(content, "<!-- AFFILIATE LIST START -->", "<!-- AFFILIATE LIST END -->", generate_affiliate_table(affiliates))
        
        all_submissions = [s for submissions in affiliates.values() for s in submissions]
        
        content = update_readme_section(content, "<!-- TOP KEY APPROACHES START -->", "<!-- TOP KEY APPROACHES END -->", 
                                        get_top_items_by_occurrences(all_submissions, 'key_approach'))
        
        content = update_readme_section(content, "<!-- TOP SUCCESSFUL STRATEGIES START -->", "<!-- TOP SUCCESSFUL STRATEGIES END -->", 
                                        get_top_items_by_occurrences(all_submissions, 'what_went_well'))
        
        content = update_readme_section(content, "<!-- COMMON CLIENT TYPES START -->", "<!-- COMMON CLIENT TYPES END -->", 
                                        get_top_items_by_occurrences(all_submissions, 'client_type', 5))
        
        content = update_readme_section(content, "<!-- PRICING INSIGHTS START -->", "<!-- PRICING INSIGHTS END -->", 
                                        generate_pricing_insights(all_submissions))
        
        content = update_readme_section(content, "<!-- AREAS FOR IMPROVEMENT START -->", "<!-- AREAS FOR IMPROVEMENT END -->", 
                                        get_top_items_by_occurrences(all_submissions, 'future_improvements', 5))
        
        content = update_readme_section(content, "<!-- ADVICE FOR AFFILIATES START -->", "<!-- ADVICE FOR AFFILIATES END -->", 
                                        get_top_items_by_occurrences(all_submissions, 'advice_for_others', 5))
        
        content = update_readme_section(content, "<!-- PROGRAM STATS START -->", "<!-- PROGRAM STATS END -->", generate_program_stats(affiliates))

        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        
    except IOError as e:
        print(f"Error updating README: {str(e)}")

def update_affiliate_readme(affiliate_tag: str, submissions: List[Submission]) -> None:
    """Create or update an individual affiliate's README with their submissions and stats."""
    readme_path = os.path.join(os.path.dirname(submissions[0].file_path), 'README.md')
    content = f"# {affiliate_tag}'s Submissions\n\n"
    content += "| Date | Agreed Price | Client Type | Sale Duration |\n"
    content += "|------|--------------|-------------|----------------|\n"

    total_sales = 0
    all_client_types = []

    for submission in sorted(submissions, key=lambda x: x.date, reverse=True):
        relative_path = os.path.relpath(submission.file_path, start=os.path.dirname(readme_path))
        content += (f"| [{submission.date.strftime(DATE_FORMAT)}]({relative_path}) | "
                    f"₦{submission.agreed_price:,} | {submission.client_type} | {submission.sale_duration} |\n")
        total_sales += submission.agreed_price
        all_client_types.append(submission.client_type)

    content += f"\n## Key Stats\n"
    content += f"- Total Submissions: {len(submissions)}\n"
    content += f"- Highest Price: ₦{max(s.agreed_price for s in submissions):,}\n"
    content += f"- Lowest Price: ₦{min(s.agreed_price for s in submissions):,}\n"
    content += f"- Most Common Client Type: {Counter(all_client_types).most_common(1)[0][0] if all_client_types else 'N/A'}\n"

    content += "\n## Top Key Approaches (by Agreed Price)\n"
    content += get_top_items_by_value(submissions, 'key_approach', 5)

    content += "\n\n## Top Successful Strategies (by Agreed Price)\n"
    content += get_top_items_by_value(submissions, 'what_went_well', 5)

    os.makedirs(os.path.dirname(readme_path), exist_ok=True)
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main() -> None:
    """Main function to orchestrate the README update process."""
    try:
        affiliates = get_affiliates_and_submissions()
        update_main_readme(affiliates)
        
        # Update individual affiliate READMEs
        for affiliate, submissions in affiliates.items():
            update_affiliate_readme(affiliate, submissions)
        
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()