import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sourcesApi, type SourceItem } from "@/api/sources";
import { foldersApi, type FolderItem } from "@/api/folders";
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

  // Field validation states (inline errors)
  const [errors, setErrors] = useState<ValidationErrors>({});

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
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto pb-20 select-none">
      {/* Back link & Title */}
      <div className="flex flex-col gap-3">
        <Link
          to="/sources"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-bold transition-colors w-fit"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Sources</span>
        </Link>
        <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
          {isNewSource ? "Register Source" : "Edit Source"}
        </h1>
      </div>

      {isLoadingData ? (
        <div className="bg-card border border-border rounded-xl p-8 shadow-2xs flex flex-col items-center justify-center gap-4 text-muted-foreground min-h-[300px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <span className="text-sm font-semibold">Loading source configurations...</span>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="bg-card border border-border rounded-xl p-6 shadow-2xs space-y-6"
        >
          {/* Telegram Reference (New Mode Only) */}
          {isNewSource ? (
            <div className="space-y-2">
              <label htmlFor="telegram_reference" className="text-sm font-bold text-foreground">
                Telegram Handle or Channel ID
              </label>
              <input
                type="text"
                id="telegram_reference"
                value={telegramReference}
                onChange={(e) => setTelegramReference(e.target.value)}
                placeholder="e.g. @telegram_channel or -10012345678"
                disabled={isSaving}
                className={cn(
                  "w-full px-3.5 py-2 border border-border bg-card rounded-md text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all",
                  errors.telegram_reference && "border-color-error focus:ring-color-error"
                )}
                autoFocus
              />
              <p className="text-xs text-muted-foreground leading-relaxed">
                Provide either the Telegram username starting with '@', or the unique numeric Telegram ID (typically starts with '-100').
              </p>
              {errors.telegram_reference && (
                <p className="text-xs text-color-error font-medium">{errors.telegram_reference}</p>
              )}
            </div>
          ) : (
            // Read-Only Reference in Edit Mode
            <div className="space-y-2">
              <label className="text-sm font-bold text-foreground">Telegram Reference</label>
              <div className="px-3.5 py-2 border border-border bg-muted-bg/60 rounded-md text-sm font-mono text-muted-foreground select-all">
                {telegramUsername ? `@${telegramUsername}` : resolvedId || "—"}
              </div>
            </div>
          )}

          {/* Display Name */}
          <div className="space-y-2">
            <label htmlFor="display_name" className="text-sm font-bold text-foreground">
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
                "w-full px-3.5 py-2 border border-border bg-card rounded-md text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all",
                errors.display_name && "border-color-error focus:ring-color-error"
              )}
            />
            {errors.display_name && (
              <p className="text-xs text-color-error font-medium">{errors.display_name}</p>
            )}

            {/* Resolved Telegram ID echo */}
            {resolvedId !== null && (
              <p className="text-xs text-muted-foreground font-semibold mt-1">
                Resolved ID: <span className="font-mono text-foreground">{resolvedId}</span>
              </p>
            )}
          </div>

          {/* Type radio button (Edit Mode Only) */}
          {!isNewSource && (
            <div className="space-y-2.5">
              <span className="text-sm font-bold text-foreground block">Source Type</span>
              <div className="flex items-center gap-6">
                <label className="inline-flex items-center gap-2 cursor-pointer text-sm font-semibold text-foreground">
                  <input
                    type="radio"
                    name="type"
                    value="channel"
                    checked={type === "channel"}
                    onChange={() => setType("channel")}
                    disabled={isSaving}
                    className="w-4 h-4 border-border text-primary focus:ring-primary"
                  />
                  <span>Channel</span>
                </label>
                <label className="inline-flex items-center gap-2 cursor-pointer text-sm font-semibold text-foreground">
                  <input
                    type="radio"
                    name="type"
                    value="group"
                    checked={type === "group"}
                    onChange={() => setType("group")}
                    disabled={isSaving}
                    className="w-4 h-4 border-border text-primary focus:ring-primary"
                  />
                  <span>Group</span>
                </label>
              </div>
              {errors.type && <p className="text-xs text-color-error font-medium">{errors.type}</p>}
            </div>
          )}

          {/* Folder dropdown */}
          <div className="space-y-2">
            <label htmlFor="folder_id" className="text-sm font-bold text-foreground">
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
                className="w-full px-3.5 py-2 border border-border bg-card rounded-md text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all cursor-pointer"
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
              <p className="text-xs text-color-error font-medium">{errors.folder_id}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border/60">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate("/sources")}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? (
                <span className="flex items-center gap-1.5 animate-fade-in">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <Save className="w-4 h-4" />
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
