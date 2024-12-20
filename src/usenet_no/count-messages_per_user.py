import mailbox
import os
import re
from collections import Counter
import csv

def extract_email(from_field):
    """
    Extracts the email address from the 'From:' field if it exists.
    """
    if not isinstance(from_field, str):
        return None
    match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
    return match.group(0) if match else None

def count_posts_per_user_in_mbox_file(mbox_file):
    """
    Counts the number of posts per user in an MBOX file.
    """
    try:
        mbox = mailbox.mbox(mbox_file)
        user_post_count = Counter()

        for message in mbox:
            from_field = message['From']
            if from_field:
                email = extract_email(from_field)
                if email:
                    user_post_count[email] += 1

        return user_post_count

    except Exception as e:
        print(f"Error processing {mbox_file}: {e}")
        return Counter()

def count_posts_per_user_in_directory(directory):
    """
    Counts the total number of posts per user across all MBOX files in a given directory.
    """
    total_post_counts = Counter()

    for filename in os.listdir(directory):
        if filename.endswith(".mbox"):
            mbox_file_path = os.path.join(directory, filename)
            post_counts = count_posts_per_user_in_mbox_file(mbox_file_path)
            total_post_counts.update(post_counts)
            print(f"Processed {filename}: {len(post_counts)} unique users in this file.")

    return total_post_counts

def export_user_post_counts_to_csv(user_post_counts, output_file):
    """
    Exports the user post counts to a CSV file.
    """
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Email", "Post Count"])
            for email, count in user_post_counts.items():
                writer.writerow([email, count])
        print(f"Exported results to {output_file}")
    except Exception as e:
        print(f"Error writing to file {output_file}: {e}")

if __name__ == "__main__":
    directory = "unzipped_data/"
    output_file = "count_messages_per_user.csv"

    # Count posts per user
    user_post_counts = count_posts_per_user_in_directory(directory)

    # Print total unique users and their counts
    print(f"Total unique users: {len(user_post_counts)}")

    # Export to CSV
    export_user_post_counts_to_csv(user_post_counts, output_file)
