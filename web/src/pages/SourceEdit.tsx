import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sourcesApi, type SourceItem } from "@/api/sources";
import { foldersApi, type FolderItem } from "@/api/folders";
import { telegramApi } from "@/api/telegram";
import { queryKeys } from "@/lib/queryKeys";
import { toast } from "sonner";
import { Button } from "@/components/shared/Button";
import { cn } from "@/lib/utils";
import { ArrowLeft, Loader2, Save } from "lucide-react";

interface ValidationErrors {
  telegram_reference?: string;
  display_name?: string;
  type?: string;
  folder_id?: string;
}

export default function SourceEdit() {
  const { id } = useParams<{ id: string }>();
  const isNewSource = !id;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Form states
  const [telegramReference, setTelegramReference] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [type, setType] = useState<"channel" | "group">("channel");
  const [folderId, setFolderId] = useState<string | null>(null);
  const [telegramUsername, setTelegramUsername] = useState<string | null>(null);
  const [resolvedId, setResolvedId] = useState<number | null>(null);
  
  // Selection vs manual input mode for Telegram Reference
  const [inputMode, setInputMode] = useState<"select" | "manual">("manual");

  // Field validation states (inline errors)
  const [errors, setErrors] = useState<ValidationErrors>({});

  // Fetch dialogs from Telegram client
  const { data: tgDialogsData, isLoading: isTgDialogsLoading } = useQuery({
    queryKey: queryKeys.telegram.dialogs(),
    queryFn: () => telegramApi.fetchDialogs(),
    enabled: isNewSource,
    staleTime: 30_000,
  });

  // Automatically update inputMode to 'select' if Telegram client is connected
  useEffect(() => {
    if (tgDialogsData) {
      if (tgDialogsData.connected) {
        setInputMode("select");
      } else {
        setInputMode("manual");
      }
    }
  }, [tgDialogsData]);

  // Fetch folders for dropdown selection
  const { data: foldersData, isLoading: isFoldersLoading } = useQuery<FolderItem[]>({
    queryKey: queryKeys.folders.list(),
    queryFn: () => foldersApi.fetchFolders(),
    staleTime: 60_000,
  });

  // Fetch source details if in edit mode
  const { data: sourceData, isLoading: isSourceLoading, isError: isSourceError } = useQuery<SourceItem>({
    queryKey: queryKeys.sources.detail(id || ""),
    queryFn: () => sourcesApi.fetchSource(id!),
    enabled: !isNewSource,
    staleTime: 0, // always fresh
  });

  // Initialize form fields when edit data loads
  useEffect(() => {
    if (!isNewSource && sourceData) {
      setDisplayName(sourceData.display_name);
      setType(sourceData.type);
      setFolderId(sourceData.folder_id);
      setTelegramUsername(sourceData.telegram_username);
      setResolvedId(sourceData.telegram_id);
    }
  }, [isNewSource, sourceData]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: async (payload: { telegram_reference: string; display_name: string }) => {
      // Step 1: POST to /sources
      const createdSource = await sourcesApi.createSource(payload);

      // Step 2: If folder selected, PATCH to /sources/{id}
      if (folderId) {
        try {
          await sourcesApi.patchSource(createdSource.id, { folder_id: folderId });
        } catch (patchErr) {
          console.error("Failed to assign folder to new source", patchErr);
          toast.warning("Source registered, but folder assignment failed.");
        }
      }

      return createdSource;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.folders.list() });
      navigate("/sources", { state: { resolvedId: data.telegram_id } });
    },
    onError: (err: any) => {
      if (err.response?.status === 422) {
        const detail = err.response?.data?.detail;
        const newErrors: ValidationErrors = {};
        if (Array.isArray(detail)) {
          detail.forEach((e: any) => {
            const path = e.loc?.[e.loc.length - 1];
            if (path) {
              newErrors[path as keyof ValidationErrors] = e.msg;
            }
          });
        }
        setErrors(newErrors);
        toast.error("Please check the form for validation errors.");
      } else {
        toast.error("Save failed — please try again.");
      }
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: {
      display_name: string;
      type: "channel" | "group";
      folder_id: string | null;
      telegram_username: string | null;
    }) => sourcesApi.updateSource(id!, payload),
    onSuccess: () => {
      toast.success("Source updated successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.detail(id!) });
      queryClient.invalidateQueries({ queryKey: queryKeys.folders.list() });
      navigate("/sources");
    },
    onError: (err: any) => {
      if (err.response?.status === 422) {
        const detail = err.response?.data?.detail;
        const newErrors: ValidationErrors = {};
        if (Array.isArray(detail)) {
          detail.forEach((e: any) => {
            const path = e.loc?.[e.loc.length - 1];
            if (path) {
              newErrors[path as keyof ValidationErrors] = e.msg;
            }
          });
        }
        setErrors(newErrors);
        toast.error("Please check the form for validation errors.");
      } else {
        toast.error("Save failed — please try again.");
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Client-side quick check
    const newErrors: ValidationErrors = {};
    if (isNewSource && !telegramReference.trim()) {
      newErrors.telegram_reference = "Telegram reference (username or numeric ID) is required.";
    }
    if (!displayName.trim()) {
      newErrors.display_name = "Display name is required.";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    if (isNewSource) {
      createMutation.mutate({
        telegram_reference: telegramReference.trim(),
        display_name: displayName.trim(),
      });
    } else {
      updateMutation.mutate({
        display_name: displayName.trim(),
        type,
        folder_id: folderId,
        telegram_username: telegramUsername,
      });
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isLoadingData = !isNewSource && isSourceLoading;

  if (isSourceError) {
    return (
      <div className="p-8 text-center bg-error-bg/15 rounded-xl border border-error-border max-w-lg mx-auto">
        <h2 className="text-lg font-bold text-color-error">Failed to load source details</h2>
        <p className="text-sm text-muted-foreground mt-2">
          The requested source could not be found or retrieved.
        </p>
        <Link
          to="/sources"
          className="mt-4 inline-flex items-center gap-1 text-sm text-primary font-bold hover:underline"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Sources Catalog</span>
        </Link>
      </div>
    );
  }  return (
    <div className="flex flex-col gap-5 max-w-2xl mx-auto pb-16 select-none animate-fade-in">
      {/* Back link & Title */}
      <div className="flex flex-col gap-1.5">
        <Link
          to="/sources"
          className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground font-semibold transition-colors w-fit"
        >
          <ArrowLeft className="w-3 h-3" />
          <span>Back to Sources</span>
        </Link>
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          {isNewSource ? "Register Source" : "Edit Source"}
        </h1>
      </div>
 
      {isLoadingData ? (
        <div className="bg-card border border-border rounded-xl p-8 shadow-premium flex flex-col items-center justify-center gap-4 text-muted-foreground min-h-[250px]">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
          <span className="text-xs font-semibold">Loading source configurations...</span>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="bg-card border border-border rounded-xl p-5 shadow-premium space-y-5"
        >
          {/* Telegram Reference (New Mode Only) */}
          {isNewSource ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-foreground uppercase tracking-wide">
                  Telegram Source Reference
                </label>
                {tgDialogsData?.connected && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setInputMode("select")}
                      className={cn(
                        "px-2.5 py-1 text-[10px] font-semibold rounded-lg border transition-all cursor-pointer select-none active:scale-[0.98]",
                        inputMode === "select"
                          ? "bg-primary border-primary text-primary-foreground font-bold"
                          : "bg-card border-border hover:bg-muted text-muted-foreground"
                      )}
                    >
                      Select from Account
                    </button>
                    <button
                      type="button"
                      onClick={() => setInputMode("manual")}
                      className={cn(
                        "px-2.5 py-1 text-[10px] font-semibold rounded-lg border transition-all cursor-pointer select-none active:scale-[0.98]",
                        inputMode === "manual"
                          ? "bg-primary border-primary text-primary-foreground font-bold"
                          : "bg-card border-border hover:bg-muted text-muted-foreground"
                      )}
                    >
                      Enter Manually
                    </button>
                  </div>
                )}
              </div>

              {inputMode === "select" && tgDialogsData?.connected ? (
                <div className="space-y-1.5 animate-fade-in">
                  {isTgDialogsLoading ? (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground py-1">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                      <span>Loading dialogs...</span>
                    </div>
                  ) : (
                    <select
                      id="telegram_select"
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val) {
                          const dialog = tgDialogsData.dialogs.find((d) => d.id === val);
                          if (dialog) {
                            setTelegramReference(dialog.username ? `@${dialog.username}` : dialog.id);
                            setDisplayName(dialog.name);
                          }
                        } else {
                          setTelegramReference("");
                        }
                      }}
                      disabled={isSaving}
                      className="w-full h-9 px-3 border border-border bg-card rounded-lg text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all cursor-pointer font-medium"
                    >
                      <option value="">Select a channel or group...</option>
                      {tgDialogsData.dialogs.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} {d.username ? `(@${d.username})` : `(ID: ${d.id})`} — {d.is_channel ? "Channel" : "Group"}
                        </option>
                      ))}
                    </select>
                  )}
                  <p className="text-[11px] text-muted-foreground leading-normal">
                    Select a channel or group linked to your logged-in Telegram account.
                  </p>
                </div>
              ) : (
                <div className="space-y-1.5 animate-fade-in">
                  <input
                    type="text"
                    id="telegram_reference"
                    value={telegramReference}
                    onChange={(e) => setTelegramReference(e.target.value)}
                    placeholder="e.g. @telegram_channel or -10012345678"
                    disabled={isSaving}
                    className={cn(
                      "w-full h-9 px-3 border border-border bg-card rounded-lg text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all",
                      errors.telegram_reference && "border-red-500 focus:ring-red-500/20"
                    )}
                    autoFocus
                  />
                  <p className="text-[11px] text-muted-foreground leading-normal">
                    Provide either the Telegram username starting with '@', or the unique numeric Telegram ID (typically starts with '-100').
                  </p>
                </div>
              )}

              {/* Offline/degraded indicator */}
              {tgDialogsData && !tgDialogsData.connected && (
                <div className="p-2.5 rounded-lg border border-warning-border bg-warning-bg/10 text-warning-foreground text-[10px] font-medium leading-normal">
                  ⚠️ Live Telegram connection is not active. Dialogue listing auto-selection is unavailable. Please enter reference handle or ID manually.
                </div>
              )}

              {errors.telegram_reference && (
                <p className="text-xs text-red-500 font-semibold mt-1">{errors.telegram_reference}</p>
              )}
            </div>
          ) : (
            // Read-Only Reference in Edit Mode
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-foreground uppercase tracking-wide">Telegram Reference</label>
              <div className="h-9 px-3 flex items-center border border-border bg-muted/30 rounded-lg text-xs font-mono text-muted-foreground select-all">
                {telegramUsername ? `@${telegramUsername}` : resolvedId || "—"}
              </div>
            </div>
          )}
 
          {/* Display Name */}
          <div className="space-y-1.5">
            <label htmlFor="display_name" className="text-xs font-bold text-foreground uppercase tracking-wide">
              Display Name
            </label>
            <input
              type="text"
              id="display_name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Tech News Feed"
              disabled={isSaving}
              className={cn(
                "w-full h-9 px-3 border border-border bg-card rounded-lg text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all",
                errors.display_name && "border-red-500 focus:ring-red-500/20"
              )}
            />
            {errors.display_name && (
              <p className="text-xs text-red-500 font-semibold">{errors.display_name}</p>
            )}
 
            {/* Resolved Telegram ID echo */}
            {resolvedId !== null && (
              <p className="text-[11px] text-muted-foreground font-semibold mt-1">
                Resolved ID: <span className="font-mono text-foreground">{resolvedId}</span>
              </p>
            )}
          </div>
 
          {/* Type radio button (Edit Mode Only) */}
          {!isNewSource && (
            <div className="space-y-2">
              <span className="text-xs font-bold text-foreground block uppercase tracking-wide">Source Type</span>
              <div className="flex items-center gap-6">
                <label className="inline-flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground select-none">
                  <input
                    type="radio"
                    name="type"
                    value="channel"
                    checked={type === "channel"}
                    onChange={() => setType("channel")}
                    disabled={isSaving}
                    className="w-4 h-4 border-border text-primary focus:ring-primary/20"
                  />
                  <span>Channel</span>
                </label>
                <label className="inline-flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground select-none">
                  <input
                    type="radio"
                    name="type"
                    value="group"
                    checked={type === "group"}
                    onChange={() => setType("group")}
                    disabled={isSaving}
                    className="w-4 h-4 border-border text-primary focus:ring-primary/20"
                  />
                  <span>Group</span>
                </label>
              </div>
              {errors.type && <p className="text-xs text-red-500 font-semibold">{errors.type}</p>}
            </div>
          )}
 
          {/* Folder dropdown */}
          <div className="space-y-1.5">
            <label htmlFor="folder_id" className="text-xs font-bold text-foreground uppercase tracking-wide">
              Folder Assignment
            </label>
            {isFoldersLoading ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground py-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                <span>Loading folders...</span>
              </div>
            ) : (
              <select
                id="folder_id"
                value={folderId || ""}
                onChange={(e) => setFolderId(e.target.value === "" ? null : e.target.value)}
                disabled={isSaving}
                className="w-full h-9 px-3 border border-border bg-card rounded-lg text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all cursor-pointer font-medium"
              >
                <option value="">None (Ungrouped)</option>
                {foldersData?.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
            )}
            {errors.folder_id && (
              <p className="text-xs text-red-500 font-semibold">{errors.folder_id}</p>
            )}
          </div>
 
          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate("/sources")}
              disabled={isSaving}
              size="sm"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving} size="sm">
              {isSaving ? (
                <span className="flex items-center gap-1.5 animate-fade-in">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Saving...
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <Save className="w-3.5 h-3.5" />
                  <span>{isNewSource ? "Register Source" : "Save Changes"}</span>
                </span>
              )}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
