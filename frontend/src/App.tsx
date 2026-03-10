/**
 * Root application component.
 * Wraps NapoleonPanel in the ThemeProvider.
 */

import { ThemeProvider } from "./hooks/useTheme";
import NapoleonPanel from "./components/NapoleonPanel";
import "./styles/global.css";

export default function App() {
  return (
    <ThemeProvider initialTheme="napoleon_gold" initialMode="dark">
      <NapoleonPanel />
    </ThemeProvider>
  );
}
