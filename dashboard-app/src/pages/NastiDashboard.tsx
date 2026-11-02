/** "नस्ती डॅशबोर्ड" tab: Abhi's नस्ती-स्थिती डॅशबोर्ड (from Nasti-Dashboard.apk, assets/public/index.html), served
 *  unchanged at /nasti/index.html and shown here in a full-height frame. Its data stays in this browser's storage
 *  (same origin as the app); Android-only features fall back to the browser's own (download, share, copy). */
export default function NastiDashboard() {
  return (
    <div className="-mx-4 -mt-4 md:-mt-6">
      <iframe
        src="/nasti/index.html"
        title="नस्ती डॅशबोर्ड"
        className="block w-full border-0 h-[calc(100dvh-8.5rem)] md:h-[100dvh]"
        allow="microphone; clipboard-write; web-share"
      />
    </div>
  );
}
