export default function Welcome({ onEnter }) {
  return (
    <div className="relative h-screen w-full overflow-hidden">
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 h-full w-full object-cover"
      >
        <source src="/bg.mp4" type="video/mp4" />
      </video>

      <div className="absolute inset-0 bg-black/60"></div>

      <div className="relative z-10 flex h-full items-center justify-center text-center text-white">
        <div className="max-w-xl px-6">
          <h1 className="mb-6 text-6xl font-bold tracking-tight">
            DNA Analyzer
          </h1>

          <p className="mb-10 text-lg text-slate-100">
            Explore DNA sequences and detect biological signals such as
            ORFs, promoters, transcription terminators and Shine-Dalgarno motifs.
          </p>

          <button
            onClick={onEnter}
            className="group inline-flex items-center gap-3 rounded-3xl bg-white px-8 py-3 text-lg font-semibold text-black shadow-lg transition-all duration-300 hover:scale-105 hover:bg-slate-100"
          >
            <span className="text-3xl font-bold transition-transform duration-300 group-hover:translate-x-1">
              →
            </span>
            Enter Application
          </button>
        </div>
      </div>
    </div>
  );
}