import { useRef, useState, useEffect, useMemo } from 'react';
import Head from 'next/head';

export default function ChatEmbedDemo() {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [affiliateId, setAffiliateId] = useState<string>('123');
  const [familyId, setFamilyId] = useState<string>('456');
  const [accentColor, setAccentColor] = useState<string>('blue');
  const [embedMethod, setEmbedMethod] = useState<'url' | 'postMessage'>('url');
  const [isEmbedded, setIsEmbedded] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [affiliateName, setAffiliateName] = useState<string>('');

  useEffect(() => {
    setIsClient(true);
  }, []);

  const origin = typeof window !== 'undefined' ? window.location.origin : '';

  const generateIframeUrl = () => {
    if (!isClient) return '';
    
    const baseUrl = origin + '/embed-chat';
    return `${baseUrl}?name=${encodeURIComponent(affiliateName)}&affiliateId=${encodeURIComponent(affiliateId)}&affiliateType=both&familyId=${encodeURIComponent(familyId)}&affiliateName=${encodeURIComponent(affiliateName)}&color=${accentColor}`;
  };

  const embedChat = () => {
    console.log('embedChat called, checking refs and state:', {
      hasIframeRef: !!iframeRef.current,
      isClient,
      embedMethod,
      affiliateId,
      familyId,
      affiliateName
    });
    
    if (!iframeRef.current || !isClient) {
      console.log('iframeRef.current or isClient is falsy, returning');
      return;
    }
    
    if (embedMethod === 'url') {
      const url = generateIframeUrl();
      console.log('Setting iframe src with URL parameters:', url);
      iframeRef.current.src = url;
    } else {
      console.log('Using postMessage method, setting base iframe src');
      iframeRef.current.src = origin + '/embed-chat';
      
      iframeRef.current.onload = () => {
        console.log('Iframe loaded, sending postMessage');
        if (!iframeRef.current?.contentWindow) {
          console.log('contentWindow is not available');
          return;
        }
        
        const message = {
          type: 'CHAT_CONFIG',
          affiliateName,
          affiliateId,
          affiliateType: 'both',
          familyId,
          accentColor
        };
        console.log('Sending postMessage:', message);
        iframeRef.current.contentWindow.postMessage(message, '*');
      };
    }
    
    console.log('Setting isEmbedded to true');
    setIsEmbedded(true);
  };

  return (
    <>
      <Head>
        <title>Chat Widget Demo</title>
      </Head>
      <main className="flex min-h-screen flex-col p-4 md:p-8 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">LiveKit Chat Widget Demo</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gray-100 p-4 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Configuration</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Embed Method</label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="embedMethod"
                    checked={embedMethod === 'url'}
                    onChange={() => setEmbedMethod('url')}
                    className="mr-2"
                  />
                  URL Parameters
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="embedMethod"
                    checked={embedMethod === 'postMessage'}
                    onChange={() => setEmbedMethod('postMessage')}
                    className="mr-2"
                  />
                  postMessage API
                </label>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Affiliate ID (int)</label>
              <input
                type="number"
                value={affiliateId}
                onChange={(e) => setAffiliateId(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="e.g., 123"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Family ID (int)</label>
              <input
                type="number"
                value={familyId}
                onChange={(e) => setFamilyId(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="e.g., 456"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Affiliate Name</label>
              <input
                type="text"
                value={affiliateName}
                onChange={(e) => setAffiliateName(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Enter affiliate name"
              />
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Accent Color</label>
              <select
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                className="w-full p-2 border rounded"
              >
                <option value="blue">Blue</option>
                <option value="green">Green</option>
                <option value="purple">Purple</option>
                <option value="red">Red</option>
                <option value="cyan">Cyan</option>
                <option value="amber">Amber</option>
              </select>
            </div>

            <button
              onClick={embedChat}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 mt-4"
            >
              {isEmbedded ? 'Update Chat Widget' : 'Load Chat Widget'}
            </button>
            
            <div className="mt-6">
              <h3 className="text-lg font-medium mb-2">How It Works</h3>
              <p className="text-sm text-gray-600 mb-2">
                This demo shows how to embed the LiveKit chat widget using two methods:
              </p>
              <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
                <li>URL Parameters: Simplest method, passing config info in the URL</li>
                <li>postMessage API: More flexible, can update widget settings dynamically</li>
              </ul>
              <p className="text-sm text-gray-600 mt-2">
                Configure the details above and click &quot;Load Chat Widget&quot; to see it in action.
              </p>
            </div>
          </div>
          
          <div className="bg-gray-100 p-4 rounded-lg flex flex-col">
            <h2 className="text-xl font-semibold mb-4">Chat Widget</h2>
            <div className="rounded-lg border border-gray-300 flex-grow overflow-hidden bg-white h-[600px]">
              <iframe
                ref={iframeRef}
                className={`w-full h-full ${isEmbedded ? 'block' : 'hidden'}`}
                frameBorder="0"
                src="about:blank"
                title="Chat Widget Embed"
              ></iframe>
              
              {!isEmbedded && (
                <div className="flex items-center justify-center h-full text-gray-500">
                  Configure and load the chat widget to see it here
                </div>
              )}
            </div>
            
            <div className="mt-4">
              <h3 className="text-lg font-medium mb-2">Embed Code</h3>
              {isClient ? (
                <div className="bg-gray-800 p-3 rounded text-white text-xs overflow-x-auto">
                  {embedMethod === 'url' ? (
                    <pre>{`<iframe
  src="${generateIframeUrl()}"
  width="100%"
  height="600px"
  frameBorder="0"
></iframe>`}</pre>
                  ) : (
                    <pre>{`<iframe id="chat-iframe" src="${origin + '/embed-chat'}" width="100%" height="600px" frameBorder="0"></iframe>
<script>
  const iframe = document.getElementById('chat-iframe');
  iframe.onload = () => {
    iframe.contentWindow.postMessage({
      type: 'CHAT_CONFIG',
      affiliateName: '${affiliateName}',
      affiliateId: '${affiliateId}',
      affiliateType: 'both',
      familyId: '${familyId}',
      accentColor: '${accentColor}'
    }, '*');
  };
</script>`}</pre>
                  )}
                </div>
              ) : (
                <div className="bg-gray-800 p-3 rounded text-white text-xs overflow-x-auto">
                  <p>Loading...</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
} 