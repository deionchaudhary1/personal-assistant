import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Today from "./pages/Today";
import Week from "./pages/Week";
import Tasks from "./pages/Tasks";
import Documents from "./pages/Documents";
import Settings from "./pages/Settings";

const queryClient = new QueryClient();

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return isActive ? "app-nav-link active" : "app-nav-link";
}

function NavBar() {
  return (
    <nav className="app-nav">
      <span className="app-brand">Personal Assistant</span>
      <div className="app-nav-links">
        <NavLink to="/" end className={navLinkClass}>
          Today
        </NavLink>
        <NavLink to="/week" className={navLinkClass}>
          Week
        </NavLink>
        <NavLink to="/tasks" className={navLinkClass}>
          Tasks
        </NavLink>
        <NavLink to="/documents" className={navLinkClass}>
          Documents
        </NavLink>
        <NavLink to="/settings" className={navLinkClass}>
          Settings
        </NavLink>
      </div>
    </nav>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-shell">
          <NavBar />
          <main className="app-main">
            <Routes>
              <Route path="/" element={<Today />} />
              <Route path="/week" element={<Week />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
