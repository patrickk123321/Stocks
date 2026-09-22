"use client";

import { useAuth } from "@clerk/nextjs";
import { UserCirclePlus } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { ActorType, addWatchlistActor, fetchWatchlistActors, GetToken, removeWatchlistActor } from "../lib/api";

function actorKey(actorType: ActorType, actorName: string): string {
  return `${actorType}:${actorName}`;
}

// Same module-level shared-cache pattern as WatchlistButton.tsx, keyed on
// "type:name" since actor identity needs both.
let cachedActors: Set<string> | null = null;
let cacheLoad: Promise<Set<string>> | null = null;

function loadActors(getToken: GetToken): Promise<Set<string>> {
  if (cachedActors) return Promise.resolve(cachedActors);
  if (!cacheLoad) {
    cacheLoad = fetchWatchlistActors(getToken).then((actors) => {
      cachedActors = new Set(actors.map((a) => actorKey(a.actor_type, a.actor_name)));
      return cachedActors;
    });
  }
  return cacheLoad;
}

export default function ActorWatchlistButton({
  actorType,
  actorName,
  size = 16,
}: {
  actorType: ActorType;
  actorName: string;
  size?: number;
}) {
  const { isSignedIn, getToken } = useAuth();
  const [following, setFollowing] = useState(false);
  const [busy, setBusy] = useState(false);
  const key = actorKey(actorType, actorName);

  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;
    loadActors(getToken).then((actors) => {
      if (!cancelled) setFollowing(actors.has(key));
    });
    return () => {
      cancelled = true;
    };
  }, [isSignedIn, key, getToken]);

  if (!isSignedIn) return null;

  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (busy) return;
    setBusy(true);
    try {
      if (following) {
        await removeWatchlistActor(actorType, actorName, getToken);
        cachedActors?.delete(key);
      } else {
        await addWatchlistActor(actorType, actorName, getToken);
        cachedActors?.add(key);
      }
      setFollowing((prev) => !prev);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      aria-pressed={following}
      aria-label={following ? `Stop following ${actorName}` : `Follow ${actorName}`}
      title={following ? `Stop following ${actorName}` : `Follow ${actorName}`}
      className="-m-1.5 flex h-7 w-7 shrink-0 items-center justify-center text-muted-foreground transition-[color,transform] duration-150 ease-out hover:text-accent active:scale-[0.97] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
    >
      <UserCirclePlus size={size} weight={following ? "fill" : "regular"} className={following ? "text-accent" : ""} aria-hidden="true" />
    </button>
  );
}
