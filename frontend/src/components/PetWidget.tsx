import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getNews } from "../api/client";
import { enablePushNotifications } from "../push";

// Five growth stages, plain-text ASCII, each 1-3 short monospace lines.
const PET_FRAMES = [
  "( . )", // 0: egg
  " (o.o)\n  )( ", // 1: hatchling
  " (o.o)\n /||\\ \n  ^^  ", // 2: juvenile
  " (^.^)\n /|||\\\n  ^ ^ ", // 3: adult
  " (*.*)\n/||||||\\\n ^  ^ ", // 4: elder
];

type PushStatus = "idle" | "enabling" | "enabled" | "denied" | "unsupported" | "failed";

function happinessMeter(happiness: number): string {
  const filled = Math.max(0, Math.min(10, Math.round(happiness / 10)));
  return `[${"|".repeat(filled)}${".".repeat(10 - filled)}]`;
}

export default function PetWidget() {
  const { data } = useQuery({
    queryKey: ["news"],
    queryFn: getNews,
    staleTime: 60 * 60 * 1000,
  });

  const [pushStatus, setPushStatus] = useState<PushStatus>("idle");

  const engagement = data?.engagement;

  async function handleEnablePush() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setPushStatus("unsupported");
      return;
    }
    setPushStatus("enabling");
    const ok = await enablePushNotifications();
    if (ok) {
      setPushStatus("enabled");
      return;
    }
    setPushStatus(Notification.permission === "denied" ? "denied" : "failed");
  }

  const pushStatusText: Record<PushStatus, string> = {
    idle: "",
    enabling: "enabling…",
    enabled: "notifications enabled",
    denied: "permission denied",
    unsupported: "not supported on this device",
    failed: "couldn't enable notifications",
  };

  return (
    <aside className="card pet-widget">
      <h2>&gt; pet_</h2>
      {!engagement && <p className="empty-state">no pet data yet.</p>}
      {engagement && (
        <>
          <pre className="pet-art">{PET_FRAMES[Math.min(4, Math.max(0, engagement.pet_stage))]}</pre>
          <p className="streak-line">
            streak: {engagement.current_streak} day{engagement.current_streak === 1 ? "" : "s"}
          </p>
          <p className="happiness-meter">{happinessMeter(engagement.pet_happiness)}</p>
        </>
      )}
      <div className="form-actions">
        <button
          type="button"
          className="btn-secondary"
          onClick={handleEnablePush}
          disabled={pushStatus === "enabling" || pushStatus === "enabled"}
        >
          enable notifications
        </button>
        {pushStatus !== "idle" && (
          <span className="inline-status">{pushStatusText[pushStatus]}</span>
        )}
      </div>
    </aside>
  );
}
