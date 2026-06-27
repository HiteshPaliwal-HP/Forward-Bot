import React, { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { foldersApi, type FolderItem } from "@/api/folders";
import { queryKeys } from "@/lib/queryKeys";
import { toast } from "sonner";
import { Button } from "@/components/shared/Button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { Loader2 } from "lucide-react";

interface FolderModalProps {
  mode: "create" | "rename" | "delete";
  folder?: FolderItem;
  onClose: () => void;
  onSuccess: () => void;
}

export default function FolderModal({ mode, folder, onClose, onSuccess }: FolderModalProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(folder?.name || "");
  const [nameError, setNameError] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  // Synchronize name if folder changes
  useEffect(() => {
    if (folder) {
      setName(folder.name);
    } else {
      setName("");
    }
  }, [folder]);

  // Debounced duplicate name check
  useEffect(() => {
    if (mode === "delete") return;
    if (!name.trim()) {
      setNameError(null);
      return;
    }
    // If renaming and the name is unchanged, there's no duplicate issue with itself
    if (mode === "rename" && folder && name.trim().toLowerCase() === folder.name.toLowerCase()) {
      setNameError(null);
      return;
    }

    const timer = setTimeout(async () => {
      setIsChecking(true);
      try {
        const results = await foldersApi.fetchFolders({ name: name.trim() });
        const exactMatch = results.find(
          (f) => f.name.toLowerCase() === name.trim().toLowerCase()
        );
        if (exactMatch && exactMatch.id !== folder?.id) {
          setNameError(`Folder name in use: ${exactMatch.name}.`);
        } else {
          setNameError(null);
        }
      } catch (err) {
        console.error("Error validating folder name", err);
      } finally {
        setIsChecking(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [name, mode, folder]);

  // Mutator for create folder
  const createMutation = useMutation({
    mutationFn: (payload: { name: string }) => foldersApi.createFolder(payload),
    onSuccess: () => {
      toast.success("Folder created successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.folders.list() });
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      if (err.response?.status === 422) {
        const detail = err.response?.data?.detail;
        const msg = typeof detail === "string" ? detail : detail?.[0]?.msg || "Folder name in use.";
        setNameError(msg);
      } else {
        const errMsg = err.response?.data?.message || err.message || "Failed to create folder.";
        toast.error(errMsg);
      }
    },
  });

  // Mutator for rename folder
  const renameMutation = useMutation({
    mutationFn: (payload: { name: string }) => foldersApi.renameFolder(folder!.id, payload),
    onSuccess: () => {
      toast.success("Folder renamed successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.folders.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.folders.detail(folder!.id) });
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      if (err.response?.status === 422) {
        const detail = err.response?.data?.detail;
        const msg = typeof detail === "string" ? detail : detail?.[0]?.msg || "Folder name in use.";
        setNameError(msg);
      } else {
        const errMsg = err.response?.data?.message || err.message || "Failed to rename folder.";
        toast.error(errMsg);
      }
    },
  });

  // Mutator for delete folder
  const deleteMutation = useMutation({
    mutationFn: () => foldersApi.deleteFolder(folder!.id),
    onSuccess: () => {
      toast.success("Folder deleted successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.folders.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.list() });
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const errMsg = err.response?.data?.message || err.message || "Failed to delete folder.";
      toast.error(errMsg);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || nameError || isChecking) return;

    if (mode === "create") {
      createMutation.mutate({ name: name.trim() });
    } else if (mode === "rename") {
      renameMutation.mutate({ name: name.trim() });
    }
  };

  const isPending = createMutation.isPending || renameMutation.isPending || deleteMutation.isPending;

  if (mode === "delete") {
    return (
      <AlertDialog open={true} onOpenChange={(open) => { if (!open) onClose(); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Folder</AlertDialogTitle>
            <AlertDialogDescription>
              Delete folder '{folder?.name}'? {folder?.source_count || 0} source(s) will be moved to Ungrouped.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={onClose} disabled={isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteMutation.mutate()}
              disabled={isPending}
            >
              {isPending ? (
                <span className="flex items-center gap-1">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Deleting...
                </span>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  }

  return (
    <Dialog open={true} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "New Folder" : "Rename Folder"}</DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Create a new folder to organize your registered sources."
              : "Change the name of the folder."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="folder_name" className="text-sm font-semibold text-foreground">
              Folder Name
            </label>
            <input
              type="text"
              id="folder_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Crypto Channels"
              disabled={isPending}
              className="w-full px-3 py-2 border border-border bg-card rounded-md text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              autoFocus
            />
            {isChecking && (
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin text-primary" />
                Checking availability...
              </p>
            )}
            {nameError && <p className="text-xs text-color-error font-medium">{nameError}</p>}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isPending || !name.trim() || !!nameError || isChecking}
            >
              {isPending ? (
                <span className="flex items-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Saving...
                </span>
              ) : mode === "create" ? (
                "Create"
              ) : (
                "Save"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
