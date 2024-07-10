import os
import re
import yaml
from datetime import datetime, date
from typing import Dict, List, NamedTuple
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# Define constants for commonly used paths and formats
AFFILIATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'affiliate_logs')
README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'README.md')
DATE_FORMAT = '%Y-%m-%d'

# Define a structure for submission data
class Submission(NamedTuple):
    date: datetime
    file_path: str
    affiliate_tag: str
    referral_count: int
    who_did_you_refer: List[str]
    brief_description: str
    referral_methods: List[str]
    specific_message: str
    conversation_summary: List[str]
    what_worked_best: List[str]
    why_they_signed_up: str
    what_you_did_well: str
    how_to_improve: str

def parse_submission_file(file_path: str) -> Submission:
    """
    Parse a submission file and extract its data into a Submission object.
    
    Args:
        file_path (str): Path to the submission file.
    
    Returns:
        Submission: A Submission object containing the parsed data or default values if parsing fails.
    """
    try:
        # Read file content and split into frontmatter and main content
        with open(file_path, 'r') as f:
            parts = f.read().split('---', 2)
        
        # Parse YAML frontmatter
        frontmatter = yaml.safe_load(parts[1])
        
        # Parse markdown sections into a dictionary
        sections = {section.split('\n')[0].strip(): '\n'.join(section.split('\n')[1:]).strip() 
                    for section in re.split(r'##\s+', parts[2]) if section.strip()}

        # Handle date parsing for both string and date object inputs
        date_value = frontmatter['date']
        submission_date = (datetime.strptime(date_value, DATE_FORMAT) if isinstance(date_value, str)
                           else datetime.combine(date_value, datetime.min.time()))

        # Construct and return the Submission object
        return Submission(
            date=submission_date,
            file_path=file_path,
            affiliate_tag=frontmatter['affiliate_tag'],
            referral_count=frontmatter['referral_count'],
            # Parse list fields, stripping markdown list indicators
            who_did_you_refer=[item.strip('- ') for item in sections.get('Who did you refer?', '').split('\n') if item.strip()],
            brief_description=sections.get('Brief description', ''),
            referral_methods=[item.strip('- ') for item in sections.get('Referral methods', '').split('\n') if item.strip()],
            specific_message=sections.get('Specific message', ''),
            # Extract links from conversation summary
            conversation_summary=re.findall(r'\[.*?\]\(.*?\)', sections.get('Conversation summary', '')),
            what_worked_best=[item.strip('- ') for item in sections.get('What worked best?', '').split('\n') if item.strip()],
            why_they_signed_up=sections.get('Why they signed up', ''),
            what_you_did_well=sections.get('What you did well', ''),
            how_to_improve=sections.get('How to improve', '')
        )
    except Exception as e:
        # Log the error and return a default Submission object
        print(f"Error parsing {file_path}: {str(e)}")
        return Submission(datetime.min, file_path, '', 0, [], '', [], '', [], [], '', '', '')
    
def get_affiliates_and_submissions() -> Dict[str, List[Submission]]:
    """
    Collect all valid submissions for each affiliate.
    
    Returns:
        Dict[str, List[Submission]]: A dictionary with affiliate tags as keys and lists of their submissions as values.
    """
    affiliates = {}
    with ThreadPoolExecutor() as executor:
        future_to_file = {
            executor.submit(parse_submission_file, os.path.join(root, file)): os.path.join(root, file)
            for root, _, files in os.walk(AFFILIATES_DIR)
            for file in files if file.endswith('_submission.md')
        }
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            submission = future.result()
            if submission.referral_count > 0:  # Only add valid submissions
                affiliates.setdefault(submission.affiliate_tag, []).append(submission)
    
    return affiliates

def update_readme_section(content: str, start_marker: str, end_marker: str, new_content: str) -> str:
    """
    Update a specific section in the README.
    
    Args:
        content (str): The entire content of the README.
        start_marker (str): The starting marker of the section to update.
        end_marker (str): The ending marker of the section to update.
        new_content (str): The new content to insert between the markers.
    
    Returns:
        str: The updated README content.
    """
    pattern = fr"({re.escape(start_marker)}).*?({re.escape(end_marker)})"
    replacement = f"\\1\n{new_content}\n\\2"
    return re.sub(pattern, replacement, content, flags=re.DOTALL)

def generate_affiliate_table(affiliates: Dict[str, List[Submission]]) -> str:
    """
    Generate the affiliate table content with links to affiliate directories and their latest submissions.
    
    Args:
        affiliates (Dict[str, List[Submission]]): Dictionary of affiliates and their submissions.
    
    Returns:
        str: Markdown formatted table of affiliates, their latest submissions, and total referrals.
    """
    table = "| Affiliate | Latest Submission | Total Referrals |\n"
    table += "|-----------|--------------------|-----------------|\n"
    for affiliate, submissions in sorted(affiliates.items(), key=lambda x: sum(s.referral_count for s in x[1]), reverse=True):
        latest_submission = max(submissions, key=lambda x: x.date)
        total_referrals = sum(submission.referral_count for submission in submissions)
        
        # Create relative paths for affiliate directory and latest submission
        affiliate_dir = os.path.relpath(os.path.join(AFFILIATES_DIR, affiliate.replace(" - ", "_")), start=os.path.dirname(README_PATH)).replace('\\', '/')
        submission_path = os.path.relpath(latest_submission.file_path, start=os.path.dirname(README_PATH)).replace('\\', '/')
        
        # Create table row with linked affiliate name and latest submission
        table += f"| [{affiliate}]({affiliate_dir}) | [{latest_submission.date.strftime(DATE_FORMAT)}]({submission_path}) | {total_referrals} |\n"
    
    return table

def get_top_items_by_referrals(submissions: List[Submission], attribute: str, n: int = 8) -> str:
    """
    Get top n items based on total referrals.
    
    Args:
        submissions (List[Submission]): List of all submissions.
        attribute (str): The attribute to analyze ('referral_methods', 'what_worked_best', or 'how_to_improve').
        n (int): Number of top items to return. Default is 8.
    
    Returns:
        str: Markdown formatted list of top items with their referral counts.
    """
    item_referrals = {}
    for submission in submissions:
        items = getattr(submission, attribute)
        if isinstance(items, list):
            for item in items:
                item_referrals[item] = item_referrals.get(item, 0) + submission.referral_count
        elif isinstance(items, str) and items:  # For 'how_to_improve'
            item_referrals[items] = item_referrals.get(items, 0) + submission.referral_count
    
    top_items = sorted(item_referrals.items(), key=lambda x: x[1], reverse=True)[:n]
    return "\n".join(f"- {item} ({referrals} referrals)" for item, referrals in top_items)

def generate_top_items(items: List[str], n: int = 8) -> str:
    """
    Generate a list of top n most common items.
    
    Args:
        items (List[str]): List of all items.
        n (int): Number of top items to return. Default is 8.
    
    Returns:
        str: Markdown formatted list of top items.
    """
    return "\n".join(f"- {item}" for item, _ in Counter(items).most_common(n))

def generate_program_stats(affiliates: Dict[str, List[Submission]]) -> str:
    """
    Generate overall program statistics.
    
    Args:
        affiliates (Dict[str, List[Submission]]): Dictionary of affiliates and their submissions.
    
    Returns:
        str: Markdown formatted list of program statistics.
    """
    total_affiliates = len(affiliates)
    total_referrals = sum(sum(s.referral_count for s in submissions) for submissions in affiliates.values())
    avg_referrals = total_referrals / total_affiliates if total_affiliates > 0 else 0
    return f"- Total Affiliates: {total_affiliates}\n- Total Referrals: {total_referrals}\n- Average Referrals per Affiliate: {avg_referrals:.2f}"

def update_main_readme(affiliates: Dict[str, List[Submission]]) -> None:
    """
    Update the main README with all sections.
    
    Args:
        affiliates (Dict[str, List[Submission]]): Dictionary of affiliates and their submissions.
    """
    try:
        with open(README_PATH, 'r') as f:
            content = f.read()
        
        # Update affiliate list
        content = update_readme_section(content, "<!-- AFFILIATE LIST START -->", "<!-- AFFILIATE LIST END -->", generate_affiliate_table(affiliates))
        
        # Get all submissions sorted by referral count
        all_submissions = [s for submissions in affiliates.values() for s in submissions]
        all_submissions.sort(key=lambda x: x.referral_count, reverse=True)
        
        # Update top referral methods
        content = update_readme_section(content, "<!-- TOP REFERRAL METHODS START -->", "<!-- TOP REFERRAL METHODS END -->", 
                                        get_top_items_by_referrals(all_submissions, 'referral_methods'))
        
        # Update most common referral types
        content = update_readme_section(content, "<!-- COMMON REFERRAL TYPES START -->", "<!-- COMMON REFERRAL TYPES END -->", 
                                        generate_top_items([ref for s in all_submissions for ref in s.who_did_you_refer]))
        
        # Update what's working best
        content = update_readme_section(content, "<!-- WHATS WORKING BEST START -->", "<!-- WHATS WORKING BEST END -->", 
                                        get_top_items_by_referrals(all_submissions, 'what_worked_best'))
        
        # Update areas for improvement
        content = update_readme_section(content, "<!-- AREAS FOR IMPROVEMENT START -->", "<!-- AREAS FOR IMPROVEMENT END -->", 
                                        get_top_items_by_referrals(all_submissions, 'how_to_improve'))
        
        # Generate tag cloud
        all_tags = [tag for s in all_submissions for tag in (s.referral_methods + s.who_did_you_refer)]
        tag_cloud = ' '.join(f'{tag}({count})' for tag, count in Counter(all_tags).most_common(20))
        content = update_readme_section(content, "<!-- TAG CLOUD START -->", "<!-- TAG CLOUD END -->", tag_cloud)
        
        # Update program stats
        content = update_readme_section(content, "<!-- PROGRAM STATS START -->", "<!-- PROGRAM STATS END -->", generate_program_stats(affiliates))

        with open(README_PATH, 'w') as f:
            f.write(content)
        
    except IOError as e:
        print(f"Error updating README: {str(e)}")

def update_affiliate_readme(affiliate_tag: str, submissions: List[Submission]) -> None:
    """
    Create or update an individual affiliate's README with their submissions and stats.
    
    Args:
        affiliate_tag (str): Tag of the affiliate.
        submissions (List[Submission]): List of the affiliate's submissions.
    """
    readme_path = os.path.join(os.path.dirname(submissions[0].file_path), 'README.md')
    content = f"# {affiliate_tag}'s Submissions\n\n"
    content += "| Date | Referral Count | Referral Methods | Who Did You Refer |\n"
    content += "|------|----------------|------------------|--------------------|\n"

    total_referrals = 0
    all_referral_methods = []
    all_who_did_you_refer = []

    for submission in sorted(submissions, key=lambda x: x.date, reverse=True):
        relative_path = os.path.relpath(submission.file_path, start=os.path.dirname(readme_path))
        content += (f"| [{submission.date.strftime(DATE_FORMAT)}]({relative_path}) | "
                    f"{submission.referral_count} | {', '.join(submission.referral_methods)} | {', '.join(submission.who_did_you_refer)} |\n")
        total_referrals += submission.referral_count
        all_referral_methods.extend(submission.referral_methods)
        all_who_did_you_refer.extend(submission.who_did_you_refer)

    content += f"\n## Key Stats\n"
    content += f"- Total Submissions: {len(submissions)}\n"
    content += f"- Total Referrals: {total_referrals}\n"
    content += f"- Top Referral Method: {Counter(all_referral_methods).most_common(1)[0][0] if all_referral_methods else 'N/A'}\n"
    content += f"- Most Common Referral Type: {Counter(all_who_did_you_refer).most_common(1)[0][0] if all_who_did_you_refer else 'N/A'}\n"

    os.makedirs(os.path.dirname(readme_path), exist_ok=True)
    with open(readme_path, 'w') as f:
        f.write(content)

def main() -> None:
    """
    Main function to orchestrate the README update process.
    """
    try:
        affiliates = get_affiliates_and_submissions()
        update_main_readme(affiliates)
        
        # Update individual affiliate READMEs
        with ThreadPoolExecutor() as executor:
            executor.map(lambda x: update_affiliate_readme(*x), affiliates.items())
        
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
