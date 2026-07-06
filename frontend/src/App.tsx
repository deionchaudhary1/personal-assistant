import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Tasks from "./pages/Tasks";
import NewsPanel from "./components/NewsPanel";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-shell">
        <header className="app-nav">
          <span className="app-brand">to-do_</span>
        </header>
        <main className="app-main app-layout">
          <Tasks />
          <NewsPanel />
        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;
