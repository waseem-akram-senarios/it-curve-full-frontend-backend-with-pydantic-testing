import { useState, useRef, ChangeEvent } from 'react';
import Head from 'next/head';
import Image from 'next/image';
import { BackToHome } from '@/components/BackToHome';

// D-ID authorization header from the existing code
const AUTHORIZATION = `Basic ZFcxaGNpNWhiR2xBYzJWdVlYSnBiM011YkdsMlpROk5NSXhSdEQxZk5abUNaUzJSM2s5Nw==`;

export default function ImageUploadPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle file selection
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const file = e.target.files?.[0];
    
    if (!file) {
      return;
    }
    
    // Validate file type
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setError('Invalid file type. Please upload a JPEG or PNG image.');
      return;
    }
    
    // Create a preview URL
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    
    // Auto-generate a valid filename
    const baseFileName = file.name
      .replace(/[^a-zA-Z0-9._-]/g, '') // Remove invalid characters
      .substring(0, 50); // Truncate to 50 chars
    setFileName(baseFileName);
  };
  
  // Handle file upload to D-ID API
  const handleUpload = async () => {
    if (!fileInputRef.current?.files?.length) {
      setError('Please select an image to upload');
      return;
    }
    
    const file = fileInputRef.current.files[0];
    setLoading(true);
    setError(null);
    
    try {
      // Create form data
      const formData = new FormData();
      formData.append('image', file);
      if (fileName) {
        formData.append('filename', fileName);
      }
      
      // Upload to D-ID API
      const response = await fetch('https://api.d-id.com/images', {
        method: 'POST',
        headers: {
          'Authorization': AUTHORIZATION,
          // Note: Do not set Content-Type for FormData
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Upload response:', data);
      
      if (data.url) {
        setUploadedImageUrl(data.url);
      } else {
        throw new Error('No URL in response');
      }
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Clear the form and start over
  const handleClear = () => {
    setPreviewUrl(null);
    setUploadedImageUrl(null);
    setFileName('');
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <>
      <Head>
        <title>D-ID Image Upload</title>
        <meta name="description" content="Upload images to D-ID API" />
      </Head>
      
      <BackToHome />
      
      <div className="min-h-screen bg-gray-900 text-white p-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">D-ID Image Upload</h1>
          
          <div className="bg-gray-800 rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Upload an Image</h2>
            <p className="text-sm text-gray-400 mb-6">
              This tool uploads an image to the D-ID API and returns a URL that you can use for creating avatars.
              <br />The image will be temporarily stored for 24-48 hours.
              <br />Supported formats: JPEG, PNG
            </p>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Select Image
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png"
                onChange={handleFileChange}
                className="w-full bg-gray-700 text-white rounded-md px-4 py-2 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            
            {fileName && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Filename (Max 50 characters, only a-z, A-Z, 0-9, ., _, -)
                </label>
                <input
                  type="text"
                  value={fileName}
                  onChange={(e) => setFileName(e.target.value.replace(/[^a-zA-Z0-9._-]/g, '').substring(0, 50))}
                  className="w-full bg-gray-700 text-white rounded-md px-4 py-2 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-green-500"
                  maxLength={50}
                />
              </div>
            )}
            
            <div className="flex flex-wrap gap-4">
              <button
                onClick={handleUpload}
                disabled={loading || !previewUrl}
                className="bg-green-600 hover:bg-green-500 text-white rounded-md py-3 px-6 font-medium transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Uploading...' : 'Upload to D-ID'}
              </button>
              
              <button
                onClick={handleClear}
                className="bg-gray-600 hover:bg-gray-500 text-white rounded-md py-3 px-6 font-medium transition-colors duration-200"
              >
                Clear
              </button>
            </div>
          </div>
          
          {previewUrl && (
            <div className="bg-gray-800 rounded-lg p-6 mb-8">
              <h2 className="text-xl font-semibold mb-4">Image Preview</h2>
              <div className="relative w-full max-w-md h-64 mx-auto border border-gray-600 rounded-lg overflow-hidden">
                <Image
                  src={previewUrl}
                  alt="Preview"
                  fill
                  style={{ objectFit: 'contain' }}
                />
              </div>
            </div>
          )}
          
          {error && (
            <div className="bg-red-900 bg-opacity-50 border border-red-700 rounded-lg p-6 mb-8">
              <h2 className="text-xl font-semibold mb-2 text-red-400">Error</h2>
              <p className="text-white">{error}</p>
            </div>
          )}
          
          {uploadedImageUrl && (
            <div className="bg-green-900 bg-opacity-20 border border-green-700 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-green-400">Upload Successful!</h2>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Image URL (Copy this to use with D-ID)
                </label>
                <div className="flex">
                  <input
                    type="text"
                    value={uploadedImageUrl}
                    readOnly
                    className="flex-1 bg-gray-700 text-white rounded-l-md px-4 py-2 border border-gray-600 focus:outline-none"
                  />
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(uploadedImageUrl);
                      alert('URL copied to clipboard!');
                    }}
                    className="bg-green-700 hover:bg-green-600 text-white rounded-r-md px-4 py-2 transition-colors duration-200"
                  >
                    Copy
                  </button>
                </div>
              </div>
              <div className="mt-8 mb-2">
                <h3 className="text-lg font-medium mb-4">Uploaded Image</h3>
                <div className="relative w-full max-w-md h-64 mx-auto border border-gray-600 rounded-lg overflow-hidden">
                  <Image
                    src={uploadedImageUrl}
                    alt="Uploaded image"
                    fill
                    style={{ objectFit: 'contain' }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
} 