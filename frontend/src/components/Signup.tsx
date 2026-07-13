import { useState } from "react";
import { register } from "../lib/api";
import { useAuth } from "../lib/store";
import { Link } from "react-router-dom";

const ROLES = [
  { value: "rm", label: "Relationship Manager" },
  { value: "credit_officer", label: "Credit Officer" },
  { value: "admin", label: "Admin" },
];

export default function Signup() {
  const setAuth = useAuth((s) => s.setAuth);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("rm");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await register(username, password, role);
      setAuth(res.access_token, res.role, username);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Could not create the account");
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
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Create your account</h1>
          <p className="text-slate-500 font-medium mt-2">
            Get started with the IDBI Fin portal
          </p>
        </div>

        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="label">Username</label>
            <input
              className="input bg-white/60 hover:bg-white focus:bg-white transition-colors"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="At least 3 characters"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              className="input bg-white/60 hover:bg-white focus:bg-white transition-colors"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="label">Role</label>
            <select
              className="input bg-white/60 hover:bg-white focus:bg-white transition-colors"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>
          {error && <div className="text-red-600 text-sm font-semibold text-center p-3 bg-red-50 border border-red-100 rounded-xl">{error}</div>}
          <button className="w-full py-3.5 text-lg font-bold text-white bg-gradient-to-r from-[#00836C] to-[#006654] hover:scale-[1.02] active:scale-[0.98] rounded-xl shadow-[0_8px_20px_rgba(0,131,108,0.3)] hover:shadow-[0_10px_25px_rgba(0,131,108,0.4)] transition-all duration-300 disabled:opacity-50 disabled:hover:scale-100" disabled={busy}>
            {busy ? "Creating account…" : "Create Account"}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="font-bold text-[#00836C] hover:text-[#006654] transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
