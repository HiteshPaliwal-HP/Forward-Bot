import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { rulesApi, type ForwardingRule, type RulesListResponse } from "@/api/rules";
import { sourcesApi } from "@/api/sources";
import { queryKeys } from "@/lib/queryKeys";
import { StatusPill, FilterIconRow } from "@/components/shared";
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
  Play, 
  Square, 
  ChevronLeft, 
  ChevronRight,
  Loader2
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function ForwardsList() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Checkbox selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  
  // Bulk Action confirmation dialog state
  const [bulkActionType, setBulkActionType] = useState<"enable" | "disable" | "delete" | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // 1. Rules Query
  const { data: rulesData, isLoading: isRulesLoading, isError: isRulesError, refetch: refetchRules } = useQuery<RulesListResponse>({
    queryKey: [...queryKeys.rules.list(), page, pageSize],
    queryFn: () => rulesApi.fetchRules({ page, page_size: pageSize }),
    staleTime: 30_000,
  });

  // 2. Sources Query to resolve source_id -> display_name
  const { data: sourcesData, isLoading: isSourcesLoading } = useQuery({
    queryKey: queryKeys.sources.list(),
    queryFn: () => sourcesApi.fetchSources({ page_size: 1000 }),
    staleTime: 60_000,
  });

  // Lookup map for source names
  const sourcesMap = useMemo(() => {
    const map = new Map<string, string>();
    if (sourcesData?.items) {
      sourcesData.items.forEach(src => {
        map.set(src.id, src.display_name);
      });
    }
    return map;
  }, [sourcesData]);

  // Optimistic Toggle Mutation
  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      isActive ? rulesApi.disableRule(id) : rulesApi.enableRule(id),

    onMutate: async ({ id, isActive }) => {
      await queryClient.cancelQueries({ queryKey: [...queryKeys.rules.list()] });
      const currentQueryKey = [...queryKeys.rules.list(), page, pageSize];
      const previousData = queryClient.getQueryData<RulesListResponse>(currentQueryKey);

      queryClient.setQueryData<RulesListResponse>(currentQueryKey, (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((rule) =>
            rule.id === id ? { ...rule, is_active: !isActive } : rule
          ),
        };
      });

      return { previousData, queryKey: currentQueryKey };
    },

    onError: (err: any, _vars, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(context.queryKey, context.previousData);
      }
      const errMsg = err.response?.data?.detail || err.response?.data?.message || err.message;
      toast.error(`Toggle failed: ${errMsg || "Please try again."}`);
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
    },
  });

  // Single Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => rulesApi.deleteRule(id),
    onSuccess: (_, deletedId) => {
      toast.success("Rule deleted successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(deletedId);
        return next;
      });
    },
    onError: (err: any) => {
      const errMsg = err.response?.data?.detail || err.response?.data?.message || err.message;
      toast.error(`Delete failed: ${errMsg || "Please try again."}`);
    }
  });

  // Handle single toggle click
  const handleToggleActive = (rule: ForwardingRule) => {
    toggleMutation.mutate({ id: rule.id, isActive: rule.is_active });
  };

  // Checkbox functions
  const handleSelectRow = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked && rulesData?.items) {
      setSelectedIds(new Set(rulesData.items.map(r => r.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const isAllSelected = useMemo(() => {
    if (!rulesData?.items || rulesData.items.length === 0) return false;
    return rulesData.items.every(r => selectedIds.has(r.id));
  }, [rulesData, selectedIds]);

  const isSomeSelected = useMemo(() => {
    if (!rulesData?.items || rulesData.items.length === 0) return false;
    return rulesData.items.some(r => selectedIds.has(r.id)) && !isAllSelected;
  }, [rulesData, selectedIds, isAllSelected]);

  // Bulk operation executor
  const executeBulkAction = async (action: "enable" | "disable" | "delete") => {
    const ids = Array.from(selectedIds);
    let completed = 0;
    let failed = 0;
    const errors: string[] = [];

    const toastId = toast.loading(`0 of ${ids.length} complete`);

    for (const id of ids) {
      try {
        if (action === "enable") {
          await rulesApi.enableRule(id);
        } else if (action === "disable") {
          await rulesApi.disableRule(id);
        } else if (action === "delete") {
          await rulesApi.deleteRule(id);
        }
        completed++;
      } catch (err: any) {
        failed++;
        const errMsg = err.response?.data?.detail || err.response?.data?.message || err.message;
        errors.push(`Rule ${id}: ${errMsg || "API error"}`);
      }
      toast.loading(`${completed + failed} of ${ids.length} complete`, { id: toastId });
    }

    if (failed === 0) {
      toast.success(`${completed} rules ${action}d successfully.`, { id: toastId });
    } else {
      toast.error(`${completed} succeeded, ${failed} failed.`, {
        id: toastId,
        duration: Infinity,
        description: (
          <div className="mt-2 text-foreground">
            <p className="font-semibold text-xs">Error details:</p>
            <details className="cursor-pointer text-[10px] max-h-32 overflow-y-auto mt-1">
              <summary className="text-muted-foreground hover:text-foreground font-semibold">[Show errors]</summary>
              <ul className="list-disc pl-3 mt-1 space-y-1 font-mono">
                {errors.map((e, idx) => (
                  <li key={idx}>{e}</li>
                ))}
              </ul>
            </details>
          </div>
        )
      });
    }

    queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
    setSelectedIds(new Set());
    setBulkActionType(null);
  };

  const triggerBulkAction = (action: "enable" | "disable" | "delete") => {
    setBulkActionType(action);
    if (action === "delete") {
      setShowConfirmDialog(true);
    } else if (action === "disable" && selectedIds.size >= 5) {
      setShowConfirmDialog(true);
    } else {
      // Enable or small disable triggers directly
      executeBulkAction(action);
    }
  };

  // Pagination totals
  const totalItems = rulesData?.total ?? 0;
  const totalPages = Math.ceil(totalItems / pageSize);

  return (
    <div className="flex flex-col gap-5 select-none relative pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-bold tracking-tight text-foreground">Forwards</h1>
          <p className="text-xs text-muted-foreground font-medium">
            Manage forwarding rules configured to route messages across Telegram channels.
          </p>
        </div>
        <Link 
          to="/forwards/new"
          className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground font-semibold rounded-lg text-xs hover:bg-color-active-hover shadow-sm active:scale-[0.98] transition-all cursor-pointer select-none"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Forward</span>
        </Link>
      </div>
 
      {/* Rules list container */}
      <div className="bg-card border border-border rounded-xl shadow-premium overflow-hidden">
        {isRulesLoading ? (
          <div className="p-8 flex flex-col items-center justify-center gap-4 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
            <span className="text-xs font-semibold">Loading forwarding rules...</span>
          </div>
        ) : isRulesError ? (
          <div className="p-8 flex flex-col items-center justify-center gap-3 border border-error-border bg-error-bg text-error text-center">
            <span className="text-xs font-bold">Failed to load forwarding rules</span>
            <button 
              onClick={() => refetchRules()}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-750 text-white rounded-lg text-xs font-semibold active:scale-[0.98] transition-all cursor-pointer shadow-3xs"
            >
              Retry
            </button>
          </div>
        ) : !rulesData?.items || rulesData.items.length === 0 ? (
          <div className="p-16 text-center border-dashed border border-border rounded-xl">
            <p className="text-xs font-semibold text-muted-foreground">No forwarding rules configured.</p>
            <p className="text-[11px] text-muted-foreground mt-1 opacity-80">
              Create a forwarding rule to start message processing.
            </p>
            <Link 
              to="/forwards/new"
              className="mt-4 inline-flex items-center gap-1.5 text-xs text-primary font-bold hover:underline"
            >
              <span>Create your first rule</span>
              <Plus className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto w-full">
            <table className="w-full text-left border-collapse min-w-[700px]">
              <thead>
                <tr className="border-b border-border bg-muted/30 text-[10px] font-bold text-muted-foreground uppercase tracking-wider select-none">
                  {/* Bulk selection checkbox */}
                  <th className="py-2.5 px-4 w-12 text-center">
                    <input 
                      type="checkbox"
                      checked={isAllSelected}
                      ref={el => {
                        if (el) el.indeterminate = isSomeSelected;
                      }}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                      className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-primary/20 cursor-pointer"
                    />
                  </th>
                  <th className="py-2.5 px-4">Source</th>
                  <th className="py-2.5 px-4">Destination</th>
                  <th className="py-2.5 px-4 w-28">Status</th>
                  <th className="py-2.5 px-4 w-36">Active Filters</th>
                  <th className="py-2.5 px-4 w-32 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-xs font-medium">
                {rulesData.items.map((rule) => {
                  const sourceName = isSourcesLoading 
                    ? "Loading..." 
                    : sourcesMap.get(rule.source_id) || rule.source_id;
 
                  // Build config for filter icon row
                  const filterConfig = {
                    time_window: rule.time_window || undefined,
                    sampling: rule.sampling || undefined,
                    media_type_filter: rule.media_type_filter || undefined,
                    block_keywords: rule.block_keywords || undefined,
                    allow_keywords: rule.allow_keywords || undefined,
                  };
 
                  return (
                    <tr 
                      key={rule.id}
                      className={cn(
                        "hover:bg-muted/40 transition-colors select-none",
                        selectedIds.has(rule.id) && "bg-primary/5 hover:bg-primary/10"
                      )}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-4 text-center">
                        <input 
                          type="checkbox"
                          checked={selectedIds.has(rule.id)}
                          onChange={() => handleSelectRow(rule.id)}
                          className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-primary/20 cursor-pointer"
                        />
                      </td>
                      {/* Source */}
                      <td className="py-3 px-4 text-foreground font-semibold max-w-[200px] truncate">
                        {sourceName}
                      </td>
                      {/* Destination */}
                      <td className="py-3 px-4 text-muted-foreground max-w-[200px] truncate">
                        {rule.destination_channel}
                      </td>
                      {/* Status */}
                      <td className="py-3 px-4 flex items-center gap-2">
                        <button
                          onClick={() => handleToggleActive(rule)}
                          disabled={toggleMutation.isPending}
                          className={cn(
                            "w-8 h-4 rounded-full p-0.5 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/20 select-none",
                            rule.is_active ? "bg-primary" : "bg-muted"
                          )}
                          aria-label={`Toggle active state. Current: ${rule.is_active ? "Active" : "Inactive"}`}
                        >
                          <div 
                            className={cn(
                              "w-3 h-3 rounded-full bg-white shadow-sm transition-transform",
                              rule.is_active ? "translate-x-4" : "translate-x-0"
                            )}
                          />
                        </button>
                        <StatusPill status={rule.is_active ? "active" : "inactive"} />
                      </td>
                      {/* Active Filters Icons */}
                      <td className="py-3 px-4">
                        <FilterIconRow config={filterConfig} />
                      </td>
                      {/* Actions */}
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center gap-2">
                          <Link
                            to={`/forwards/${rule.id}/edit`}
                            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            title="Edit Forwarding Rule"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </Link>
                          <button
                            onClick={() => {
                              if (confirm("Are you sure you want to delete this rule?")) {
                                deleteMutation.mutate(rule.id);
                              }
                            }}
                            className="p-1 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors cursor-pointer"
                            title="Delete Forwarding Rule"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
 
      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-border/60 pt-4 px-2">
          <span className="text-[11px] font-semibold text-muted-foreground">
            Showing Page <span className="text-foreground">{page}</span> of <span className="text-foreground">{totalPages}</span> ({totalItems} total rules)
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1 border border-border rounded-lg hover:bg-muted disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed select-none transition-colors"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1 border border-border rounded-lg hover:bg-muted disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed select-none transition-colors"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
 
      {/* Sticky Sliding Bulk Action Bar */}
      <div 
        className={cn(
          "fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-card/90 backdrop-blur-md border border-border shadow-premium px-5 py-2.5 rounded-xl flex items-center gap-5 transition-all duration-300 transform",
          selectedIds.size > 0 ? "translate-y-0 opacity-100 animate-fade-in" : "translate-y-24 opacity-0 pointer-events-none"
        )}
      >
        <span className="text-xs font-semibold text-foreground">
          {selectedIds.size} selected
        </span>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <button
            onClick={() => triggerBulkAction("enable")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-success-bg text-success-foreground border border-success-border rounded-lg text-xs font-semibold hover:bg-success-border/50 active:scale-[0.98] transition-all cursor-pointer"
          >
            <Play className="w-3 h-3 fill-current animate-pulse" />
            <span>Enable</span>
          </button>
          <button
            onClick={() => triggerBulkAction("disable")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-warning-bg text-warning-foreground border border-warning-border rounded-lg text-xs font-semibold hover:bg-warning-border/50 active:scale-[0.98] transition-all cursor-pointer"
          >
            <Square className="w-3 h-3 fill-current" />
            <span>Disable</span>
          </button>
          <button
            onClick={() => triggerBulkAction("delete")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-error-bg text-degraded-foreground border border-error-border rounded-lg text-xs font-semibold hover:bg-error-border/50 active:scale-[0.98] transition-all cursor-pointer"
          >
            <Trash2 className="w-3 h-3" />
            <span>Delete</span>
          </button>
        </div>
      </div>
 
      {/* Custom AlertDialog for Bulk Actions */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Confirm Bulk {bulkActionType === "delete" ? "Delete" : "Disable"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {bulkActionType === "delete" 
                ? `Are you sure you want to delete ${selectedIds.size} forwarding rules? This action is permanent and cannot be undone.` 
                : `You are disabling ${selectedIds.size} forwarding rules simultaneously. This will suspend message routing across all these rules. Are you sure you want to proceed?`
              }
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setShowConfirmDialog(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => {
                setShowConfirmDialog(false);
                if (bulkActionType) executeBulkAction(bulkActionType);
              }}
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
