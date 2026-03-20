export default function DisclaimerBanner() {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-100 border-t border-gray-300 z-50">
      <div className="max-w-7xl mx-auto px-4 py-2">
        <p className="text-xs text-gray-600 text-center">
          LexAI outputs are for research purposes only and do not constitute legal advice. 
          Always verify with primary sources and consult a qualified lawyer before acting on any information.
        </p>
      </div>
    </div>
  );
}
