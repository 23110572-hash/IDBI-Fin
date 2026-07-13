import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans selection:bg-[#00836C]/20 selection:text-[#00836C] overflow-hidden">
      {/* Navbar */}
      <nav className="border-b border-slate-200/50 bg-white/80 backdrop-blur-xl sticky top-0 z-50 animate-fade-in-up">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-32">
            <div className="flex items-center gap-2 group cursor-pointer shrink-0">
              <img src="/logo.png" alt="IDBI Fin Logo" className="h-28 w-auto object-contain drop-shadow-sm group-hover:drop-shadow-md transition-all duration-300" />
            </div>
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-sm font-bold text-slate-600 hover:text-[#00836C] transition-colors px-2">
                Sign In
              </Link>
              <Link to="/signup" className="btn text-white bg-gradient-to-r from-[#F58220] to-[#f79d4f] hover:from-[#e37113] hover:to-[#F58220] shadow-lg shadow-[#F58220]/30 hover:shadow-[#F58220]/50 hover:scale-105 transition-all px-6 py-2.5 rounded-full font-bold text-sm">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative pt-32 pb-20 sm:pt-40 sm:pb-24">
        {/* Background Blobs without mix-blend */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#00836C]/20 rounded-full blur-3xl animate-blob"></div>
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-[#F58220]/20 rounded-full blur-3xl animate-blob" style={{ animationDelay: '2s' }}></div>
        <div className="absolute -bottom-8 left-1/3 w-96 h-96 bg-[#00836C]/10 rounded-full blur-3xl animate-blob" style={{ animationDelay: '4s' }}></div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="animate-fade-in-up">
            <div className="inline-block mb-6 px-4 py-1.5 rounded-full bg-[#F58220]/10 border border-[#F58220]/20 text-[#F58220] font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(245,130,32,0.15)]">
              🚀 Next-Generation Risk Analytics
            </div>
          </div>
          <h1 className="text-5xl sm:text-7xl font-extrabold text-slate-900 tracking-tight mb-8 animate-fade-in-up">
            MSME Financial Health <br className="hidden sm:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00836C] via-[#00a98f] to-[#F58220]">
              with Ultimate Precision
            </span>
          </h1>
          <p className="max-w-2xl mx-auto text-lg sm:text-xl text-slate-600 mb-10 leading-relaxed animate-fade-in-up">
            The most advanced credit intelligence platform tailored for NTC and NTB borrowers. Turn raw banking data into confident lending decisions.
          </p>
          <div className="flex justify-center gap-4 animate-fade-in-up">
            <Link to="/signup" className="btn text-white bg-gradient-to-r from-[#00836C] to-[#006654] hover:scale-105 text-lg px-8 py-3 rounded-full shadow-xl shadow-[#00836C]/30 hover:shadow-[#00836C]/50 transition-all duration-300 font-bold">
              Get Started
            </Link>
            <a href="#features" className="btn-ghost text-lg px-8 py-3 rounded-full border border-slate-200 hover:border-[#00836C]/30 hover:bg-[#00836C]/5 hover:text-[#00836C] transition-all duration-300 font-bold">
              Explore Features
            </a>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div id="features" className="bg-white py-24 sm:py-32 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fade-in-up">
            <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">Everything you need to scale</h2>
            <p className="mt-4 text-lg text-slate-600">Advanced AI and robust data integration at your fingertips.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                title: "Portfolio Heat Maps",
                desc: "Visualize risk across your entire portfolio instantly with our dynamic heat maps.",
                icon: (
                  <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                )
              },
              {
                title: "Real-time Alerts",
                desc: "Stay ahead of defaults with real-time early warning signals and notifications.",
                icon: (
                  <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                )
              },
              {
                title: "Borrower Drilldown",
                desc: "Deep dive into financial health with granular data and alternative credit scoring.",
                icon: (
                  <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 21h7a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v11m0 5l4.879-4.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242z" />
                  </svg>
                )
              }
            ].map((f, i) => (
              <div key={i} className="group bg-slate-50 rounded-2xl p-8 border border-slate-100 hover:border-[#F58220]/30 hover:shadow-2xl hover:shadow-[#F58220]/10 transition-all duration-500 transform hover:-translate-y-2 animate-fade-in-up">
                <div className="w-16 h-16 rounded-2xl bg-[#00836C]/10 text-[#00836C] group-hover:bg-[#F58220] group-hover:text-white flex items-center justify-center mb-6 transition-colors duration-500 shadow-inner">
                  {f.icon}
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3 group-hover:text-[#F58220] transition-colors">{f.title}</h3>
                <p className="text-slate-600 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-slate-900 py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center mb-8 cursor-pointer hover:scale-105 transition-transform duration-300">
            <img src="/logo.png" alt="IDBI Fin Logo" className="h-24 w-auto object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]" />
          </div>
          <p className="text-slate-400 text-sm">© 2026 IDBI Innovate. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
