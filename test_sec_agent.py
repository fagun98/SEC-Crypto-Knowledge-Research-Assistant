"""
Test script for SEC Meeting Report Agent
"""

from sec_meeting_agent import generate_meeting_report
import os

if __name__ == "__main__":
    # Test with provided URL and transcript
    test_url = "https://www.sec.gov/newsroom/meetings-events/defi-american-spirit"
    test_transcript = "june_9_2025.txt"

    test_url = "https://www.sec.gov/newsroom/meetings-events/tokenization-moving-assets-onchain-where-tradfi-defi-meet"
    test_transcript = "may_12_2025.txt"

    test_url = "https://www.sec.gov/newsroom/meetings-events/know-your-custodian-key-considerations-crypto-custody"
    test_transcript = "april_28_2025.txt"
    
    # test_url = "https://www.sec.gov/newsroom/meetings-events/between-block-hard-place-tailoring-regulation-crypto-trading"
    # test_transcript = "april_11_2025.txt"
    
    test_url = "https://www.sec.gov/newsroom/meetings-events/how-we-got-here-how-we-get-out-defining-security-status"
    test_transcript = "march_21_2025.txt"
    
    # Check if transcript file exists
    if not os.path.exists(test_transcript):
        print(f"Error: Transcript file '{test_transcript}' not found.")
        print("Please ensure the transcript file is in the current directory.")
        exit(1)
    
    print("SEC Round Table Meeting Report Agent - Test")
    print("=" * 80)
    print(f"\nMeeting URL: {test_url}")
    print(f"Transcript File: {test_transcript}")
    print("\nGenerating report...")
    print("(This may take a few minutes as the agent analyzes the transcript)")
    print("-" * 80)
    
    try:
        output_file = generate_meeting_report(
            meeting_url=test_url,
            transcript_file=test_transcript,
            output_format="txt"
        )
        
        print(f"\n✓ Report generated successfully!")
        print(f"✓ Output file: {output_file}")
        print(f"\nYou can now view the report at: {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"\n✗ Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()
