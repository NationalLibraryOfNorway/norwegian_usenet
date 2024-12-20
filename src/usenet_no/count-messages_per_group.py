import mailbox
import os
import csv

def count_messages_in_mbox_file(mbox_file):
    """
    Counts the number of messages in an MBOX file.
    """
    try:
        mbox = mailbox.mbox(mbox_file)
        return len(mbox)
    except Exception as e:
        print(f"Error processing {mbox_file}: {e}")
        return 0

def count_messages_in_directory(directory):
    """
    Counts the total number of messages in all MBOX files in a given directory.
    """
    channel_message_counts = {}

    for filename in os.listdir(directory):
        if filename.endswith(".mbox"):
            mbox_file_path = os.path.join(directory, filename)
            message_count = count_messages_in_mbox_file(mbox_file_path)
            channel_message_counts[filename] = message_count
            print(f"Processed {filename}: {message_count} messages so far.")

    return channel_message_counts

def export_channel_message_counts_to_csv(channel_message_counts, output_file):
    """
    Exports the message counts per channel to a CSV file.
    """
    try:
        total_messages = sum(channel_message_counts.values())
        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Channel", "Message Count"])
            
            for channel, count in channel_message_counts.items():
                writer.writerow([channel, count])
            
            # Add a total row
            writer.writerow(["Total", total_messages])
        print(f"Exported results to {output_file}")
    except Exception as e:
        print(f"Error writing to file {output_file}: {e}")

if __name__ == "__main__":
    directory = "unzipped_data/"
    output_file = "count_messages_per_group.csv"

    # Count messages in each channel
    channel_message_counts = count_messages_in_directory(directory)

    # Print total number of messages
    total_messages = sum(channel_message_counts.values())
    print(f"Total messages across all channels: {total_messages}")

    # Export to CSV
    export_channel_message_counts_to_csv(channel_message_counts, output_file)

