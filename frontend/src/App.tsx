import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/store";
import Login from "./components/Login";
import Layout from "./components/Layout";
import NewApplication from "./components/NewApplication";
import PortfolioHeatMap from "./components/PortfolioHeatMap";
import BorrowerDrilldown from "./components/BorrowerDrilldown";
import AlertFeed from "./components/AlertFeed";
import LandingPage from "./components/LandingPage";

export default function App() {
  const token = useAuth((s) => s.token);
  
  if (!token) {
    return (
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/apply" replace />} />
        <Route path="/apply" element={<NewApplication />} />
        <Route path="/portfolio" element={<PortfolioHeatMap />} />
        <Route path="/borrower/:urn" element={<BorrowerDrilldown />} />
        <Route path="/alerts" element={<AlertFeed />} />
        <Route path="*" element={<Navigate to="/apply" replace />} />
      </Routes>
    </Layout>
  );
}
