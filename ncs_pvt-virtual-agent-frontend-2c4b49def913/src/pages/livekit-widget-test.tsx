import Head from "next/head";

export default function LivekitWidgetTestPage() {
  // Example widget URL with query params including new fields
  const widgetUrl = "/widget?affiliateId=65&affiliateType=both&familyId=3&affiliateName=ARMON&name=ARMON&accentColor=green&phoneNo=1234567890&userID=user123&clientID=client456";
  return (
    <>
      <Head>
        <title>Livekit Widget Test</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <main className="min-h-screen bg-gray-100 p-4">
        <h1 className="text-2xl font-bold mb-4">ITCurves Widget</h1>
        <p className="mb-6 text-gray-600">This page embeds the new floating Widget via iframe for development and testing.</p>
        <div className="mb-8 p-4 bg-white rounded shadow">
          <h2 className="text-lg font-semibold mb-2">Widget Parameters</h2>
          <p className="mb-2 text-sm text-gray-600">The widget supports the following parameters:</p>
          <ul className="list-disc pl-5 text-sm">
            <li><span className="font-mono bg-gray-100 px-1">affiliateId</span> - ID of the affiliate</li>
            <li><span className="font-mono bg-gray-100 px-1">affiliateType</span> - Type of affiliate</li>
            <li><span className="font-mono bg-gray-100 px-1">familyId</span> - Family ID</li>
            <li><span className="font-mono bg-gray-100 px-1">affiliateName</span> - Name of the affiliate</li>
            <li><span className="font-mono bg-gray-100 px-1">name</span> - Display name</li>
            <li><span className="font-mono bg-gray-100 px-1">accentColor</span> - Widget accent color</li>
            <li><span className="font-mono bg-gray-100 px-1">phoneNo</span> - Users phone number</li>
            <li><span className="font-mono bg-gray-100 px-1">userID</span> - Unique user identifier</li>
            <li><span className="font-mono bg-gray-100 px-1">clientID</span> - Client identifier</li>
          </ul>
        </div>
        
        <div className="mb-8 p-4 bg-white rounded shadow">
          <h2 className="text-lg font-semibold mb-2">Metadata</h2>
          <p className="mb-2 text-sm text-gray-600">The following metadata is sent to LiveKit when connecting:</p>
          <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto">
{`{
  "phoneNo": "1234567890",
  "clientID": "client456",
  "userID": "user123",
  "affiliateId": "65",
  "affiliateType": "both",
  "familyId": "3",
  "affiliateName": "ARMON"
}`}
          </pre>
          <p className="mt-2 text-sm text-gray-600">This metadata is attached to the participant in LiveKit and can be accessed by server-side code.</p>
        </div>
        {/* Floating iframe in the bottom right */}
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            width: 400,
            height: 600,
            zIndex: 1000,
            background: "transparent",
            border: "none",
            pointerEvents: "auto",
          }}
        >
          <iframe
            src={widgetUrl}
            title="Livekit Widget Iframe"
            style={{
              width: "100%",
              height: "100%",
              border: "none",
              background: "transparent",
              pointerEvents: "auto",
            }}
            allow="camera; microphone; clipboard-write"
          />
        </div>
      </main>
    </>
  );
} 