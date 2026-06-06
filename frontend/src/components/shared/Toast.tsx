import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface ToastContextType {
  toast: (message: string) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  const [visible, setVisible] = useState(false);
  const [timer, setTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  const toast = useCallback(
    (msg: string) => {
      if (timer) clearTimeout(timer);
      setMessage(msg);
      setVisible(true);
      const t = setTimeout(() => setVisible(false), 2200);
      setTimer(t);
    },
    [timer],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast — matches prototype .toast */}
      <div className={`toast ${visible ? "show" : ""}`}>
        {message}
      </div>
    </ToastContext.Provider>
  );
}
