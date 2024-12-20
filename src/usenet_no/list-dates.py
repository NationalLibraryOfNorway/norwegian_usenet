import mailbox
import os
import re

def extract_date_from_message(message):
    """
    Extracts the date from the 'Date' field of a message.
    Returns the date as a string in 'YYYY/MM/DD' format if present.
    """
    if 'Date' in message:
        date_field = message['Date']
        match = re.search(r'\d{4}/\d{2}/\d{2}', date_field)
        if match:
            return match.group(0)
    return None

def extract_dates_from_mbox_file(mbox_file):
    """
    Extracts all dates from messages in an MBOX file.
    """
    try:
        mbox = mailbox.mbox(mbox_file)
        dates = []

        for message in mbox:
            date = extract_date_from_message(message)
            if date:
                dates.append(date)

        return dates

    except Exception as e:
        print(f"Error processing {mbox_file}: {e}")
        return []

def extract_dates_from_directory(directory):
    """
    Extracts all dates from all MBOX files in a directory.
    """
    all_dates = []

    for filename in os.listdir(directory):
        if filename.endswith(".mbox"):
            mbox_file_path = os.path.join(directory, filename)
            dates = extract_dates_from_mbox_file(mbox_file_path)
            all_dates.extend(dates)
            print(f"Processed {filename}: {len(dates)} dates found.")

    return sorted(all_dates)

def save_dates_to_file(dates, output_file):
    """
    Saves the sorted list of dates to a text file.
    """
    try:
        with open(output_file, mode='w', encoding='utf-8') as file:
            for date in dates:
                file.write(f"{date}\n")
        print(f"Exported sorted dates to {output_file}")
    except Exception as e:
        print(f"Error writing to file {output_file}: {e}")

if __name__ == "__main__":
    directory = "unzipped_data/"
    output_file = "sorted_dates.txt"

    # Extract and sort dates
    sorted_dates = extract_dates_from_directory(directory)

    # Print the number of dates found
    print(f"Total dates extracted: {len(sorted_dates)}")

    # Save to file
    save_dates_to_file(sorted_dates, output_file)

