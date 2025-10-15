import { useRouter } from "next/router";
import FloatingLivekitWidget from "@/components/livekitWidget/FloatingLivekitWidget";
import Head from "next/head";

export default function WidgetPage() {
  const router = useRouter();
  const {
    affiliateId,
    affiliateType,
    familyId,
    affiliateName,
    name,
    accentColor,
    phoneNo,
    userID,
    clientID,
  } = router.query;

  // Wait for router to be ready to avoid hydration mismatch
  if (!router.isReady) return null;

  return (
    <>
      <Head>
        <style>{`
          html, body, #__next {
            background: transparent !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            min-height: 0 !important;
            height: 100% !important;
          }
        `}</style>
      </Head>
      <FloatingLivekitWidget
        affiliateId={affiliateId as string}
        
        familyId={familyId as string}
        affiliateName={affiliateName as string}
        name={name as string}
        accentColor={accentColor as string}
        phoneNo={phoneNo as string}
        userID={userID as string}
        clientID={clientID as string}
      />
    </>
  );
} 