"""
Test script for SEC Overall Report Agent
"""

from sec_overall_report_agent import generate_overall_report
import os

if __name__ == "__main__":
    print("SEC Round Table Meetings - Overall Report Agent - Test")
    print("=" * 80)
    
    # Check if any meeting reports exist
    import glob
    report_files = glob.glob("SEC_Meeting_Report_*.txt")
    
    if not report_files:
        print("Error: No meeting report files found.")
        print("Please ensure you have generated meeting reports first using sec_meeting_agent.py")
        print("Pattern: SEC_Meeting_Report_*.txt")
        exit(1)
    
    print(f"\nFound {len(report_files)} meeting report file(s):")
    for idx, file in enumerate(report_files, 1):
        print(f"  {idx}. {os.path.basename(file)}")
    
    print("\nGenerating overall report...")
    print("(This may take several minutes as the agent analyzes all reports)")
    print("-" * 80)
    
    try:
        output_file = generate_overall_report(
            report_directory=".",
            output_format="md"
        )
        
        print(f"\n✓ Overall report generated successfully!")
        print(f"✓ Output file: {output_file}")
        print(f"\nYou can now view the report at: {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"\n✗ Error generating overall report: {str(e)}")
        import traceback
        traceback.print_exc()
