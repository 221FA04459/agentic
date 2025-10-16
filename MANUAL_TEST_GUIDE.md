# Manual Test Guide for Agentic AI Compliance Officer

## Quick Test Steps

### 1. Start the Backend
```powershell
# In PowerShell (from project root)
& .\.venv\Scripts\Activate.ps1
$env:GEMINI_API_KEY="AIzaSyD_ILxOPbYAcMPch2OvIUhLGT3a8GHa8hg"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 2. Start the Frontend (in a new terminal)
```powershell
# In PowerShell (from project root)
& .\.venv\Scripts\Activate.ps1
streamlit run frontend/app.py
```

### 3. Test the System

#### Option A: Automated Test
```powershell
# Run the comprehensive test
python test_compliance_system.py
```

#### Option B: Manual Test via Streamlit UI

1. **Open Streamlit**: Go to http://localhost:8501

2. **Upload Document**:
   - Click "Upload Regulation Document"
   - Upload the `sample_gdpr.txt` file
   - Set Regulation Type: `gdpr`
   - Set Jurisdiction: `EU`
   - Set Effective Date: `2018-05-25`
   - Click "Upload & Analyze"

3. **Check Compliance**:
   - Go to "Compliance Check" tab
   - Enter the Regulation ID from step 2
   - Add company policies:
     ```
     We collect only necessary personal data for business purposes
     Data is stored securely with encryption
     Users can request data deletion
     We have a privacy policy published on our website
     Data is not shared with third parties without consent
     ```
   - Click "Check Compliance"

4. **Generate Report**:
   - Go to "Reports" tab
   - Enter the Regulation ID
   - Select format (PDF or Excel)
   - Check "Include Recommendations"
   - Click "Generate Report"
   - Download the report

## Expected Results

### ✅ Successful Test Indicators:
- **Upload**: "Uploaded. Background processing started."
- **Compliance Check**: Shows compliance score (60-75%), gaps, and recommendations
- **Report Generation**: "Report generated successfully" with download button
- **No "Analysis failed" messages**

### ❌ Common Issues:
- **"Regulation not found"**: Upload a new document first
- **"Analysis failed"**: Check your GEMINI_API_KEY
- **Connection errors**: Make sure backend is running on port 8000

## Test Data

### Sample Company Policies:
```
We collect only necessary personal data for business purposes
Data is stored securely with encryption
Users can request data deletion
We have a privacy policy published on our website
Data is not shared with third parties without consent
We conduct regular security audits
We have incident response procedures
We provide data portability options
```

### Sample Regulation Types:
- `gdpr` - General Data Protection Regulation
- `ccpa` - California Consumer Privacy Act
- `sox` - Sarbanes-Oxley Act
- `hipaa` - Health Insurance Portability and Accountability Act
- `pci` - Payment Card Industry Data Security Standard

## Troubleshooting

### Backend Issues:
```powershell
# Check if backend is running
curl http://localhost:8000/

# Check logs
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level debug
```

### Frontend Issues:
```powershell
# Check if frontend is running
curl http://localhost:8501/

# Restart frontend
streamlit run frontend/app.py --server.port 8501
```

### API Key Issues:
```powershell
# Test API key
$env:GEMINI_API_KEY="your_key_here"
python -c "import os; print('Key set:', bool(os.getenv('GEMINI_API_KEY')))"
```

## Performance Expectations

- **Document Upload**: 2-5 seconds
- **Document Processing**: 3-10 seconds (background)
- **Compliance Check**: 5-15 seconds
- **Report Generation**: 2-8 seconds
- **Total Workflow**: 15-30 seconds

## Success Criteria

✅ **System is working if:**
- Documents upload successfully
- Compliance checks return structured data (not "Analysis failed")
- Reports generate and download properly
- All API endpoints respond correctly
- No critical errors in logs

🎉 **System is production-ready if:**
- All test cases pass
- Reports contain meaningful analysis
- UI is responsive and user-friendly
- Error handling works properly
