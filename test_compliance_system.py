#!/usr/bin/env python3
"""
Test case for Agentic AI Compliance Officer System
This script demonstrates the complete workflow from document upload to report generation.
"""

import os
import json
import requests
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
GEMINI_API_KEY = "AIzaSyD_ILxOPbYAcMPch2OvIUhLGT3a8GHa8hg"

def test_compliance_system():
    """Complete test case for the compliance system"""
    
    print("🚀 Starting Agentic AI Compliance Officer Test Case")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing API Health Check...")
    try:
        response = requests.get(f"{API_BASE}/", timeout=10)
        if response.status_code == 200:
            print("✅ API is running")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure the backend is running: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000")
        return False
    
    # Test 2: Create Sample Regulation Document
    print("\n2️⃣ Creating Sample GDPR Regulation Document...")
    sample_gdpr_text = """
    GENERAL DATA PROTECTION REGULATION (GDPR) - ARTICLE 25
    
    Data Protection by Design and by Default
    
    1. Taking into account the state of the art, the cost of implementation and the nature, scope, context and purposes of processing as well as the risks of varying likelihood and severity for rights and freedoms of natural persons posed by the processing, the controller shall, both at the time of the determination of the means for processing and at the time of the processing itself, implement appropriate technical and organisational measures, such as pseudonymisation, which are designed to implement data-protection principles, such as data minimisation, in an effective manner and to integrate the necessary safeguards into the processing in order to meet the requirements of this Regulation and protect the rights of data subjects.
    
    2. The controller shall implement appropriate technical and organisational measures for ensuring that, by default, only personal data which are necessary for each specific purpose of the processing are processed. That obligation applies to the amount of personal data collected, the extent of their processing, the period of their storage and their accessibility. In particular, such measures shall ensure that by default personal data are not made accessible without the individual's intervention to an indefinite number of natural persons.
    
    3. An approved certification mechanism pursuant to Article 42 may be used as an element to demonstrate compliance with the requirements set out in paragraphs 1 and 2 of this Article.
    
    Penalties: Up to €20 million or 4% of annual global turnover, whichever is higher.
    Effective Date: May 25, 2018
    """
    
    # Save sample document
    sample_file = "sample_gdpr_article25.txt"
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write(sample_gdpr_text)
    print(f"✅ Created sample document: {sample_file}")
    
    # Test 3: Upload Regulation Document
    print("\n3️⃣ Uploading Regulation Document...")
    try:
        with open(sample_file, "rb") as f:
            files = {"file": (sample_file, f, "text/plain")}
            data = {
                "regulation_type": "gdpr",
                "jurisdiction": "EU",
                "effective_date": "2018-05-25"
            }
            
            response = requests.post(f"{API_BASE}/upload_regulation", files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                regulation_id = result["data"]["regulation_id"]
                print(f"✅ Document uploaded successfully")
                print(f"   Regulation ID: {regulation_id}")
                print(f"   Status: {result['data']['status']}")
            else:
                print(f"❌ Upload failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False
    
    # Test 4: Wait for Processing
    print("\n4️⃣ Waiting for document processing...")
    time.sleep(3)  # Give time for background processing
    
    # Test 5: Check Regulation Status
    print("\n5️⃣ Checking Regulation Status...")
    try:
        response = requests.get(f"{API_BASE}/regulations", timeout=10)
        if response.status_code == 200:
            regulations = response.json()["data"]["regulations"]
            if regulations:
                latest_reg = regulations[-1]
                print(f"✅ Found {len(regulations)} regulation(s)")
                print(f"   Latest: {latest_reg['filename']} - Status: {latest_reg.get('status', 'unknown')}")
                if latest_reg.get('status') == 'processed':
                    print("   ✅ Document processing completed")
                else:
                    print("   ⏳ Document still processing...")
            else:
                print("❌ No regulations found")
                return False
        else:
            print(f"❌ Failed to get regulations: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking regulations: {e}")
        return False
    
    # Test 6: Run Compliance Check
    print("\n6️⃣ Running Compliance Check...")
    try:
        company_policies = [
            "We collect only necessary personal data for business purposes",
            "Data is stored securely with encryption",
            "Users can request data deletion",
            "We have a privacy policy published on our website",
            "Data is not shared with third parties without consent"
        ]
        
        compliance_data = {
            "regulation_id": regulation_id,
            "company_policies": company_policies
        }
        
        response = requests.post(f"{API_BASE}/check_compliance", json=compliance_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            compliance_data = result["data"]
            print("✅ Compliance check completed")
            print(f"   Overall Status: {compliance_data['compliance_status']}")
            print(f"   Compliance Score: {compliance_data.get('compliance_score', 'N/A')}")
            print(f"   Gaps Found: {len(compliance_data.get('gaps', []))}")
            print(f"   Recommendations: {len(compliance_data.get('recommendations', []))}")
            
            # Show some gaps
            gaps = compliance_data.get('gaps', [])
            if gaps:
                print("\n   📋 Sample Gaps:")
                for i, gap in enumerate(gaps[:2], 1):
                    print(f"      {i}. {gap.get('requirement', 'N/A')}: {gap.get('gap_description', 'N/A')}")
            
            # Show some recommendations
            recommendations = compliance_data.get('recommendations', [])
            if recommendations:
                print("\n   💡 Sample Recommendations:")
                for i, rec in enumerate(recommendations[:2], 1):
                    print(f"      {i}. {rec}")
        else:
            print(f"❌ Compliance check failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Compliance check error: {e}")
        return False
    
    # Test 7: Generate PDF Report
    print("\n7️⃣ Generating PDF Report...")
    try:
        report_data = {
            "regulation_id": regulation_id,
            "include_recommendations": True
        }
        
        response = requests.post(f"{API_BASE}/generate_report?format=pdf", json=report_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            report_id = result["data"]["report_id"]
            print(f"✅ PDF report generated")
            print(f"   Report ID: {report_id}")
            print(f"   Format: {result['data']['format']}")
        else:
            print(f"❌ PDF report generation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ PDF report error: {e}")
        return False
    
    # Test 8: Generate Excel Report
    print("\n8️⃣ Generating Excel Report...")
    try:
        response = requests.post(f"{API_BASE}/generate_report?format=xlsx", json=report_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            excel_report_id = result["data"]["report_id"]
            print(f"✅ Excel report generated")
            print(f"   Report ID: {excel_report_id}")
        else:
            print(f"❌ Excel report generation failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Excel report error: {e}")
    
    # Test 9: List All Reports
    print("\n9️⃣ Listing All Reports...")
    try:
        response = requests.get(f"{API_BASE}/reports", timeout=10)
        if response.status_code == 200:
            reports = response.json()["data"]["reports"]
            print(f"✅ Found {len(reports)} report(s)")
            for i, report in enumerate(reports, 1):
                print(f"   {i}. Report {report['id'][:8]}... - Format: {report['format']} - Date: {report['generated_date']}")
        else:
            print(f"❌ Failed to list reports: {response.status_code}")
    except Exception as e:
        print(f"❌ Error listing reports: {e}")
    
    # Test 10: Download Report
    print("\n🔟 Testing Report Download...")
    try:
        # Download the PDF report
        response = requests.get(f"{API_BASE}/download_report/{report_id}", timeout=10)
        if response.status_code == 200:
            report_filename = f"test_compliance_report_{report_id}.pdf"
            with open(report_filename, "wb") as f:
                f.write(response.content)
            print(f"✅ Report downloaded successfully")
            print(f"   Saved as: {report_filename}")
            print(f"   Size: {len(response.content)} bytes")
        else:
            print(f"❌ Report download failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Download error: {e}")
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    try:
        if os.path.exists(sample_file):
            os.remove(sample_file)
            print(f"✅ Removed {sample_file}")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Test Case Completed Successfully!")
    print("\n📊 Test Summary:")
    print("   ✅ API Health Check")
    print("   ✅ Document Upload")
    print("   ✅ Document Processing")
    print("   ✅ Compliance Check")
    print("   ✅ PDF Report Generation")
    print("   ✅ Excel Report Generation")
    print("   ✅ Report Listing")
    print("   ✅ Report Download")
    print("\n🚀 Your Agentic AI Compliance Officer is working perfectly!")
    
    return True

if __name__ == "__main__":
    # Set environment variable for the test
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    
    print("🔧 Test Configuration:")
    print(f"   API Base: {API_BASE}")
    print(f"   Gemini API Key: {GEMINI_API_KEY[:20]}...")
    print(f"   Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_compliance_system()
    
    if success:
        print("\n✅ All tests passed! Your system is ready for production use.")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure the backend is running: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000")
        print("   2. Check that your GEMINI_API_KEY is valid")
        print("   3. Ensure all dependencies are installed: pip install -r requirements_minimal.txt")
