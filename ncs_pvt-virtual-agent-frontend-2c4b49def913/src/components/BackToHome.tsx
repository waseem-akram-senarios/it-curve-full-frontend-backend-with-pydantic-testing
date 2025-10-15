import Link from 'next/link';

export const BackToHome = () => {
  return (
    <Link 
      href="/" 
      className="fixed top-4 left-4 z-50 bg-gray-800 hover:bg-gray-700 text-white rounded-md px-3 py-1 text-sm flex items-center gap-1 shadow-md"
    >
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        className="h-4 w-4" 
        fill="none" 
        viewBox="0 0 24 24" 
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
      Home
    </Link>
  );
}; 