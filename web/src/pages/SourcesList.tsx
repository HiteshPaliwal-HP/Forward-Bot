import { useState, useMemo, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sourcesApi, type SourceItem, type SourcesListResponse } from "@/api/sources";
import { foldersApi, type FolderItem } from "@/api/folders";
import { rulesApi, type RulesListResponse } from "@/api/rules";
import { queryKeys } from "@/lib/queryKeys";
import FolderModal from "@/components/FolderModal";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import {
  Plus,
  Edit,
  Trash2,
  Folder,
  FolderOpen,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  FolderPlus,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function SourcesList() {
  const queryClient = useQueryClient();
  const location = useLocation();
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Selected folder state: undefined = All, null = Ungrouped, string = specific folder_id
  const [selectedFolderId, setSelectedFolderId] = useState<string | null | undefined>(undefined);

  // Folder modal state
  const [folderModal, setFolderModal] = useState<{
    open: boolean;
    mode: "create" | "rename" | "delete";
    folder?: FolderItem;
  }>({ open: false, mode: "create" });

  // Delete source state
  const [sourceToDelete, setSourceToDelete] = useState<SourceItem | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // 409 Guard state (rules conflict)
  const [conflictRules, setConflictRules] = useState<any[]>([]);
  const [showConflictDialog, setShowConflictDialog] = useState(false);
  const [isFetchingConflicts, setIsFetchingConflicts] = useState(false);

  // Success message toast on mount if redirected from create
  useEffect(() => {
    if (location.state && typeof location.state === "object" && "resolvedId" in location.state) {
      const stateObj = location.state as { resolvedId: string | number };
      toast.success(`Source registered successfully. (Resolved ID: ${stateObj.resolvedId})`);
      // Clear navigation state
      window.history.replaceState({}, document.title);
    }
  }, [location]);

  // Queries
  const {
    data: sourcesData,
    isLoading: isSourcesLoading,
    isError: isSourcesError,
    refetch: refetchSources,
  } = useQuery<SourcesListResponse>({
    queryKey: [...queryKeys.sources.list(), page, pageSize, selectedFolderId],
    queryFn: () =>
      sourcesApi.fetchSources({
        page,
        page_size: pageSize,
        folder_id: selectedFolderId === undefined ? undefined : selectedFolderId,
      }),
    staleTime: 60_000,
  });

  const {
    data: foldersData,
    isLoading: isFoldersLoading,
    isError: isFoldersError,
    refetch: refetchFolders,
  } = useQuery<FolderItem[]>({
    queryKey: queryKeys.folders.list(),
    queryFn: () => foldersApi.fetchFolders(),
    staleTime: 60_000,
  });

  // Folder names lookup map
  const foldersMap = useMemo(() => {
    const map = new Map<string, string>();
    if (foldersData) {
      foldersData.forEach((f) => {
        map.set(f.id, f.name);
      });
    }
    return map;
  }, [foldersData]);

  // Count active rules using cached query data
  const getActiveRuleCount = (sourceId: string): string => {
    const cachedQueries = queryClient.getQueriesData<RulesListResponse>({
      queryKey: queryKeys.rules.list(),
    });

    let count = 0;
    let hasCache = false;

    for (const [_, data] of cachedQueries) {
      if (data?.items) {
        hasCache = true;
        count += data.items.filter((r) => r.source_id === sourceId && r.is_active).length;
      }
    }

    return hasCache ? count.toString() : "–";
  };

  // Delete mutation
  const deleteSourceMutation = useMutation({
    mutationFn: (id: string) => sourcesApi.deleteSource(id),
    onSuccess: () => {
      toast.success("Source deleted successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.folders.list() });
      setSourceToDelete(null);
    },
    onError: async (err: any, sourceId: string) => {
      // 409 conflict: source in use by rules
      if (err.response?.status === 409) {
        setIsFetchingConflicts(true);
        setShowConflictDialog(true);
        try {
          const rulesData = await rulesApi.fetchRules({ source_id: sourceId });
          setConflictRules(rulesData.items || []);
        } catch (fetchErr) {
          console.error("Failed to fetch conflicting rules", fetchErr);
          toast.error("Could not fetch conflicting rules list.");
        } finally {
          setIsFetchingConflicts(false);
        }
      } else {
        const errMsg = err.response?.data?.message || err.message || "Failed to delete source.";
        toast.error(errMsg);
      }
      setSourceToDelete(null);
    },
  });

  const handleDeleteConfirm = () => {
    if (sourceToDelete) {
      deleteSourceMutation.mutate(sourceToDelete.id);
      setShowDeleteConfirm(false);
    }
  };

  // Reset page when folder selection changes
  const handleFolderChange = (folderId: string | null | undefined) => {
    setSelectedFolderId(folderId);
    setPage(1);
  };

  const totalItems = sourcesData?.total ?? 0;
  const totalPages = Math.ceil(totalItems / pageSize);



  return (
    <div className="flex flex-col gap-6 relative pb-20 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground animate-fade-in">Sources</h1>
          <p className="text-sm text-muted-foreground font-medium">
            Register and organize Telegram source channels and groups.
          </p>
        </div>
        <Link
          to="/sources/new"
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground font-bold rounded-lg text-sm hover:bg-color-active-hover shadow active:scale-[0.98] transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Register Source</span>
        </Link>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Left Rail (Folders) */}
        <aside className="w-full lg:w-64 shrink-0 bg-card border border-border rounded-xl p-4 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Folders</h2>
            <button
              onClick={() => setFolderModal({ open: true, mode: "create" })}
              className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              title="New Folder"
            >
              <FolderPlus className="w-4 h-4" />
            </button>
          </div>

          <nav className="space-y-1">
            {/* All Folder Tab */}
            <button
              onClick={() => handleFolderChange(undefined)}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 text-sm font-semibold rounded-lg transition-all text-left cursor-pointer",
                selectedFolderId === undefined
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <span className="flex items-center gap-2">
                {selectedFolderId === undefined ? (
                  <FolderOpen className="w-4 h-4" />
                ) : (
                  <Folder className="w-4 h-4" />
                )}
                <span>All Sources</span>
              </span>
            </button>

            {/* Folder list items */}
            {isFoldersLoading ? (
              <div className="py-4 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                <span>Loading folders...</span>
              </div>
            ) : isFoldersError ? (
              <p className="py-2 text-center text-xs text-color-error font-medium">
                Failed to load folders.
              </p>
            ) : (
              foldersData?.map((folder) => {
                const isSelected = selectedFolderId === folder.id;
                return (
                  <div
                    key={folder.id}
                    className={cn(
                      "group w-full flex items-center justify-between px-3 py-2 text-sm font-semibold rounded-lg transition-all text-left",
                      isSelected
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <button
                      onClick={() => handleFolderChange(folder.id)}
                      className="flex-1 flex items-center gap-2 overflow-hidden text-left cursor-pointer"
                    >
                      {isSelected ? (
                        <FolderOpen className="w-4 h-4 shrink-0" />
                      ) : (
                        <Folder className="w-4 h-4 shrink-0" />
                      )}
                      <span className="truncate pr-1">{folder.name}</span>
                    </button>

                    <div className="flex items-center gap-1.5 shrink-0 ml-2">
                      <span
                        className={cn(
                          "text-xs px-1.5 py-0.5 rounded-full font-bold",
                          isSelected
                            ? "bg-primary-foreground/20 text-primary-foreground"
                            : "bg-muted-bg text-muted-foreground group-hover:bg-color-border"
                        )}
                      >
                        {folder.source_count}
                      </span>
                      <button
                        onClick={() =>
                          setFolderModal({ open: true, mode: "rename", folder })
                        }
                        className={cn(
                          "p-0.5 rounded-md hover:bg-black/10 hover:text-foreground transition-colors cursor-pointer",
                          isSelected ? "text-primary-foreground" : "opacity-0 group-hover:opacity-100"
                        )}
                        title="Rename folder"
                      >
                        <Edit className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() =>
                          setFolderModal({ open: true, mode: "delete", folder })
                        }
                        className={cn(
                          "p-0.5 rounded-md hover:bg-black/10 hover:text-color-error transition-colors cursor-pointer",
                          isSelected ? "text-primary-foreground" : "opacity-0 group-hover:opacity-100"
                        )}
                        title="Delete folder"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}

            {/* Ungrouped Folder Tab */}
            <button
              onClick={() => handleFolderChange(null)}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 text-sm font-semibold rounded-lg transition-all text-left cursor-pointer",
                selectedFolderId === null
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <span className="flex items-center gap-2">
                {selectedFolderId === null ? (
                  <FolderOpen className="w-4 h-4" />
                ) : (
                  <Folder className="w-4 h-4" />
                )}
                <span>Ungrouped</span>
              </span>
            </button>
          </nav>
        </aside>

        {/* Sources Main Catalog */}
        <main className="flex-1 w-full bg-card border border-border rounded-xl shadow-2xs overflow-hidden">
          {isSourcesLoading ? (
            <div className="p-16 flex flex-col items-center justify-center gap-4 text-muted-foreground">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
              <span className="text-sm font-semibold">Loading sources...</span>
            </div>
          ) : isSourcesError ? (
            <div className="p-12 flex flex-col items-center justify-center gap-3 bg-error-bg/20 text-center">
              <AlertTriangle className="w-10 h-10 text-color-error" />
              <span className="text-sm font-bold text-color-error">Failed to load sources catalog</span>
              <button
                onClick={() => refetchSources()}
                className="px-4 py-1.5 bg-primary text-white rounded-md text-xs font-bold hover:bg-color-active-hover active:scale-[0.98] transition-all cursor-pointer shadow-3xs"
              >
                Retry
              </button>
            </div>
          ) : !sourcesData?.items || sourcesData.items.length === 0 ? (
            <div className="p-20 text-center border-dashed border border-border rounded-xl">
              <FolderOpen className="w-12 h-12 text-muted-foreground/45 mx-auto mb-4" />
              <p className="text-sm font-bold text-muted-foreground">No sources found in this view.</p>
              <p className="text-xs text-muted-foreground mt-1.5 opacity-80">
                Register a new channel or select another folder.
              </p>
              <Link
                to="/sources/new"
                className="mt-4 inline-flex items-center gap-1.5 text-xs text-primary font-bold hover:underline"
              >
                <span>Register your first source</span>
                <Plus className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <div className="flex flex-col">
              <div className="overflow-x-auto w-full">
                <table className="w-full text-left border-collapse min-w-[700px]">
                  <thead>
                    <tr className="border-b border-border bg-muted-bg text-xs font-bold text-muted-foreground uppercase tracking-wider select-none">
                      <th className="py-3 px-4">Display Name</th>
                      <th className="py-3 px-4">Telegram Handle / ID</th>
                      <th className="py-3 px-4 w-28">Type</th>
                      <th className="py-3 px-4">Folder</th>
                      <th className="py-3 px-4 w-36 text-center">Active Rules</th>
                      <th className="py-3 px-4 w-32 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-sm font-medium">
                    {sourcesData.items.map((src) => {
                      const folderName = src.folder_id ? foldersMap.get(src.folder_id) || "–" : "–";
                      return (
                        <tr key={src.id} className="hover:bg-muted-bg/50 transition-colors">
                          {/* Display Name */}
                          <td className="py-3.5 px-4 text-foreground font-bold max-w-[200px] truncate">
                            {src.display_name}
                          </td>
                          {/* Telegram Reference */}
                          <td className="py-3.5 px-4 text-muted-foreground font-mono text-xs">
                            {src.telegram_username ? `@${src.telegram_username}` : src.telegram_id}
                          </td>
                          {/* Type badge */}
                          <td className="py-3.5 px-4">
                            <span className="capitalize text-xs font-bold px-2 py-0.5 rounded bg-muted text-muted-foreground">
                              {src.type}
                            </span>
                          </td>
                          {/* Folder badge */}
                          <td className="py-3.5 px-4 text-muted-foreground">
                            {src.folder_id ? (
                              <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                                {folderName}
                              </span>
                            ) : (
                              <span className="text-muted-foreground/60">—</span>
                            )}
                          </td>
                          {/* Active Rules count */}
                          <td className="py-3.5 px-4 text-center font-bold text-foreground">
                            {getActiveRuleCount(src.id)}
                          </td>
                          {/* Actions */}
                          <td className="py-3.5 px-4">
                            <div className="flex items-center justify-center gap-2">
                              <Link
                                to={`/sources/${src.id}/edit`}
                                className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted-bg transition-colors"
                                title="Edit Source"
                              >
                                <Edit className="w-4 h-4" />
                              </Link>
                              <button
                                onClick={() => {
                                  setSourceToDelete(src);
                                  setShowDeleteConfirm(true);
                                }}
                                className="p-1.5 rounded-md text-muted-foreground hover:text-color-error hover:bg-error-bg/60 transition-colors cursor-pointer"
                                title="Delete Source"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t border-border/60 p-4">
                  <span className="text-xs font-semibold text-muted-foreground">
                    Showing Page <span className="text-foreground">{page}</span> of{" "}
                    <span className="text-foreground">{totalPages}</span> ({totalItems} total sources)
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-1.5 border border-border rounded-md hover:bg-muted disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors"
                      title="Previous Page"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="p-1.5 border border-border rounded-md hover:bg-muted disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors"
                      title="Next Page"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Folder modal */}
      {folderModal.open && (
        <FolderModal
          mode={folderModal.mode}
          folder={folderModal.folder}
          onClose={() => setFolderModal((prev) => ({ ...prev, open: false }))}
          onSuccess={() => {
            refetchFolders();
            refetchSources();
          }}
        />
      )}

      {/* Delete Source Confirmation Dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Source Channel</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete source channel "{sourceToDelete?.display_name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 409 Conflict Dialog (Active Rules Found) */}
      <AlertDialog open={showConflictDialog} onOpenChange={setShowConflictDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-color-error">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>Cannot Delete Source</span>
            </AlertDialogTitle>
            <AlertDialogDescription>
              This source channel is currently in use by active forwarding rules. You must delete or reconfigure these rules before deleting this source.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="my-4 border border-border rounded-md overflow-hidden bg-muted-bg/40 max-h-48 overflow-y-auto">
            {isFetchingConflicts ? (
              <div className="p-4 flex items-center justify-center gap-2 text-muted-foreground text-xs font-semibold">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span>Checking conflicting rules...</span>
              </div>
            ) : conflictRules.length === 0 ? (
              <p className="p-4 text-xs text-muted-foreground text-center">No rules detail found.</p>
            ) : (
              <div className="divide-y divide-border">
                {conflictRules.map((rule) => (
                  <div key={rule.id} className="p-3 flex items-center justify-between gap-4 text-xs hover:bg-muted-bg/85 transition-colors">
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <span className="font-semibold text-foreground truncate">
                        To: {rule.destination_channel}
                      </span>
                      <span className="text-muted-foreground font-mono text-[10px] truncate">
                        Rule ID: {rule.id}
                      </span>
                    </div>
                    <Link
                      to={`/forwards/${rule.id}/edit`}
                      className="inline-flex items-center gap-1 text-primary font-bold hover:underline shrink-0"
                    >
                      <span>Jump to rule</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel className="w-full sm:w-auto" onClick={() => setShowConflictDialog(false)}>
              Close
            </AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
