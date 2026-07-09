import { useState } from "react";
import { login } from "../lib/api";
import { useAuth } from "../lib/store";
import { Link } from "react-router-dom";

export default function Login() {
  const setAuth = useAuth((s) => s.setAuth);
  const [username, setUsername] = useState("rm");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await login(username, password);
      setAuth(res.access_token, res.role, username);
    } catch {
      setError("Invalid credentials");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-slate-50 relative overflow-hidden">
      {/* Animated Background Blobs */}
      <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-[#00836C]/20 rounded-full blur-3xl animate-blob"></div>
      <div className="absolute bottom-0 left-1/4 w-[600px] h-[600px] bg-[#F58220]/20 rounded-full blur-3xl animate-blob" style={{ animationDelay: '2s' }}></div>

      <div className="w-full max-w-md p-8 bg-white/80 backdrop-blur-2xl rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.08)] border border-white/50 relative z-10 animate-fade-in-up">
        <div className="text-center mb-8 flex flex-col items-center">
          <Link to="/" className="inline-block mb-6 hover:scale-105 transition-transform duration-300">
            <img src="/logo.png" alt="IDBI Fin Logo" className="h-32 w-auto object-contain drop-shadow-md" />
          </Link>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Welcome back</h1>
          <p className="text-slate-500 font-medium mt-2">
            Sign in to access the IDBI Fin portal
          </p>
        </div>
        
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="label">Username</label>
            <input 
              className="input bg-white/60 hover:bg-white focus:bg-white transition-colors" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              className="input bg-white/60 hover:bg-white focus:bg-white transition-colors"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="rm123! (dev)"
            />
          </div>
          {error && <div className="text-red-600 text-sm font-semibold text-center p-3 bg-red-50 border border-red-100 rounded-xl">{error}</div>}
          <button className="w-full py-3.5 text-lg font-bold text-white bg-gradient-to-r from-[#00836C] to-[#006654] hover:scale-[1.02] active:scale-[0.98] rounded-xl shadow-[0_8px_20px_rgba(0,131,108,0.3)] hover:shadow-[0_10px_25px_rgba(0,131,108,0.4)] transition-all duration-300 disabled:opacity-50 disabled:hover:scale-100" disabled={busy}>
            {busy ? "Authenticating…" : "Sign In to Portal"}
          </button>
        </form>
        
      </div>
    </div>
  );
}
