import { useState, useEffect, useRef, useMemo } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  rulesApi, 
  type ForwardingRule, 
  type RuleCreatePayload,
  type ReplacementRulePayload
} from "@/api/rules";
import { sourcesApi } from "@/api/sources";
import { mediaApi } from "@/api/media";
import { queryKeys } from "@/lib/queryKeys";
import { CollapsiblePanel, ActivationBanner, Button } from "@/components/shared";
import { toast } from "sonner";
import { 
  Save, 
  X, 
  Plus, 
  Edit, 
  Trash2, 
  Loader2, 
  Info,
  FolderOpen
} from "lucide-react";
import { cn } from "@/lib/utils";

// API error mapping helper skipped "body"
interface ApiValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

const mapApiErrors = (detail: ApiValidationError[]): Record<string, string> => {
  const errors: Record<string, string> = {};
  for (const err of detail) {
    const path = err.loc.filter(l => l !== "body").join(".");
    errors[path] = err.msg;
  }
  return errors;
};

const DEFAULT_RULE: RuleCreatePayload = {
  source_id: "",
  destination_channel: "",
  is_active: false,
  keyword_match_mode: "literal",
  block_keywords: [],
  allow_keywords: [],
  media_type_filter: ["text", "photo"],
  remove_links: false,
  remove_hashtags: false,
  remove_mentions: false,
  forward_media: "forward",
  sampling: { n: 1 },
  time_window: null,
  attribution: { enabled: false, position: "prefix", format: "From {source_name}" },
  auto_replace_source_refs: { enabled: false, replacement: null, replace_display_name: false },
  media_replacement: { enabled: false, replacement_image_path: null, replacement_caption_mode: "use_source" },
};

export default function ForwardEdit() {
  const { id } = useParams<{ id: string }>();
  const isNewRule = !id;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [searchParams, setSearchParams] = useSearchParams();
  const [apiErrors, setApiErrors] = useState<Record<string, string>>({});

  // 1. Fetch rule data if edit mode
  const { data: ruleData, isLoading: isRuleLoading, isError: isRuleError } = useQuery<ForwardingRule>({
    queryKey: queryKeys.rules.detail(id || ""),
    queryFn: () => rulesApi.fetchRule(id!),
    enabled: !isNewRule,
    staleTime: 0, // Always fresh on mount
  });

  // 2. Fetch sources list
  const { data: sourcesData } = useQuery({
    queryKey: queryKeys.sources.list(),
    queryFn: () => sourcesApi.fetchSources({ page_size: 1000 }),
    staleTime: 60_000,
  });

  // 3. Fetch replacements list for panel 7 (only when rule edit mode)
  const { data: replacementsData, refetch: refetchReplacements } = useQuery({
    queryKey: queryKeys.rules.replacements(id || ""),
    queryFn: () => rulesApi.fetchReplacementRules(id!),
    enabled: !isNewRule,
    staleTime: 0,
  });

  // Form State
  const [formData, setFormData] = useState<RuleCreatePayload>(DEFAULT_RULE);
  const attributionFormatInputRef = useRef<HTMLInputElement>(null);

  // Sync Form State from fetched data
  useEffect(() => {
    if (ruleData) {
      setFormData({
        source_id: ruleData.source_id,
        destination_channel: ruleData.destination_channel,
        is_active: ruleData.is_active,
        keyword_match_mode: ruleData.keyword_match_mode,
        block_keywords: ruleData.block_keywords,
        allow_keywords: ruleData.allow_keywords,
        media_type_filter: ruleData.media_type_filter,
        remove_links: ruleData.remove_links,
        remove_hashtags: ruleData.remove_hashtags,
        remove_mentions: ruleData.remove_mentions,
        forward_media: ruleData.forward_media,
        sampling: ruleData.sampling,
        time_window: ruleData.time_window,
        attribution: ruleData.attribution,
        auto_replace_source_refs: ruleData.auto_replace_source_refs,
        media_replacement: ruleData.media_replacement,
      });
    }
  }, [ruleData]);

  // Sync open panels via query search parameters
  const activePanels = useMemo(() => {
    return new Set(searchParams.get("panels")?.split(",") || []);
  }, [searchParams]);

  const togglePanel = (panelKey: string) => {
    const next = new Set(activePanels);
    if (next.has(panelKey)) {
      next.delete(panelKey);
    } else {
      next.add(panelKey);
    }
    const param = Array.from(next).join(",");
    setSearchParams(param ? { panels: param } : {}, { replace: true });
  };

  // Image replacement Combobox gallery state
  const [showImageBrowser, setShowImageBrowser] = useState(false);
  const [imageSearch, setImageSearch] = useState("");
  const { data: availableImages = [] } = useQuery({
    queryKey: queryKeys.media.replacementImages(),
    queryFn: mediaApi.fetchReplacementImages,
    enabled: formData.media_replacement.enabled,
  });

  // Filtered Image List
  const filteredImages = useMemo(() => {
    return availableImages.filter(img => 
      img.toLowerCase().includes(imageSearch.toLowerCase())
    );
  }, [availableImages, imageSearch]);

  // Replacement Rules inline editing states
  const [newRepRule, setNewRepRule] = useState<ReplacementRulePayload>({
    search_text: "",
    replacement_text: "",
    match_mode: "literal",
    is_active: true,
  });
  const [editingRepId, setEditingRepId] = useState<string | null>(null);
  const [editingRepData, setEditingRepData] = useState<ReplacementRulePayload>({
    search_text: "",
    replacement_text: "",
    match_mode: "literal",
    is_active: true,
  });

  // Mutations
  const createRuleMutation = useMutation({
    mutationFn: (payload: RuleCreatePayload) => rulesApi.createRule(payload),
    onSuccess: () => {
      toast.success("Rule created successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
      navigate("/forwards");
    },
    onError: (err: any) => {
      if (err.response?.status === 422 && err.response?.data?.detail) {
        setApiErrors(mapApiErrors(err.response.data.detail));
        toast.error("Validation failed. Please correct the fields.");
      } else {
        toast.error("Save failed — please try again.");
      }
    }
  });

  const updateRuleMutation = useMutation({
    mutationFn: (payload: RuleCreatePayload) => rulesApi.updateRule(id!, payload),
    onSuccess: () => {
      toast.success("Rule updated successfully.");
      queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.rules.detail(id!) });
      navigate("/forwards");
    },
    onError: (err: any) => {
      if (err.response?.status === 422 && err.response?.data?.detail) {
        setApiErrors(mapApiErrors(err.response.data.detail));
        toast.error("Validation failed. Please correct the fields.");
      } else {
        toast.error("Save failed — please try again.");
      }
    }
  });

  const activateMutation = useMutation({
    mutationFn: () => rulesApi.enableRule(id!),
    onSuccess: () => {
      toast.success("Rule activated!");
      queryClient.invalidateQueries({ queryKey: queryKeys.rules.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.rules.detail(id!) });
    },
    onError: (err: any) => {
      toast.error(`Activation failed: ${err.message}`);
    }
  });

  // Submit Handler
  const handleSubmit = () => {
    setApiErrors({});
    if (isNewRule) {
      createRuleMutation.mutate(formData);
    } else {
      updateRuleMutation.mutate(formData);
    }
  };

  // Keyboard and Esc listeners
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showImageBrowser) {
          setShowImageBrowser(false);
        } else if (editingRepId) {
          setEditingRepId(null);
        }
      } else if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [formData, showImageBrowser, editingRepId]);

  // Insert chip tokens at cursor helper
  const handleInsertToken = (token: string) => {
    const input = attributionFormatInputRef.current;
    if (input) {
      const start = input.selectionStart ?? 0;
      const end = input.selectionEnd ?? 0;
      const format = formData.attribution.format;
      const nextFormat = format.substring(0, start) + token + format.substring(end);
      
      setFormData(prev => ({
        ...prev,
        attribution: { ...prev.attribution, format: nextFormat }
      }));

      // Focus back and set cursor
      setTimeout(() => {
        input.focus();
        input.setSelectionRange(start + token.length, start + token.length);
      }, 0);
    } else {
      setFormData(prev => ({
        ...prev,
        attribution: { ...prev.attribution, format: prev.attribution.format + token }
      }));
    }
  };

  // Live Attribution Preview Helper
  const attributionPreview = useMemo(() => {
    if (!formData.attribution.enabled) return null;
    const format = formData.attribution.format || "";
    return format
      .replace(/{source_name}/g, "Sample Channel")
      .replace(/{source_username}/g, "sample_channel_username");
  }, [formData.attribution]);

  // Dynamically generated summary labels
  const getPanelSummary = (panelKey: string): string => {
    switch (panelKey) {
      case "basic": {
        const src = sourcesData?.items.find(s => s.id === formData.source_id);
        const sourceStr = src ? src.display_name : (formData.source_id || "Unselected");
        const destStr = formData.destination_channel || "Unset";
        const filtersStr = formData.media_type_filter.join(", ") || "none";
        return formData.source_id ? `${sourceStr} → ${destStr} (${filtersStr})` : "Not configured";
      }
      case "time": {
        if (!formData.time_window) return "Inactive";
        const days = formData.time_window.days_of_week.map(d => d.substring(0, 3)).join(", ");
        return `${days} ${formData.time_window.start_time}–${formData.time_window.end_time} ${formData.time_window.timezone}`;
      }
      case "sampling":
        return formData.sampling.n > 1 ? `Every ${formData.sampling.n}th message` : "Inactive (forward all)";
      case "keywords": {
        const block = formData.block_keywords.length;
        const allow = formData.allow_keywords.length;
        return block > 0 || allow > 0 ? `${block} blocked / ${allow} allowed` : "Inactive";
      }
      case "transforms": {
        const list: string[] = [];
        if (formData.remove_links) list.push("no-links");
        if (formData.remove_hashtags) list.push("no-tags");
        if (formData.remove_mentions) list.push("no-mentions");
        if (formData.forward_media !== "forward") list.push(`media: ${formData.forward_media}`);
        if (formData.media_replacement.enabled) list.push("replacement image");
        return list.length > 0 ? list.join(", ") : "No transforms";
      }
      case "attribution":
        return formData.attribution.enabled ? `${formData.attribution.position}: ${formData.attribution.format}` : "Inactive";
      case "replacements": {
        const count = replacementsData?.items.length || 0;
        return count > 0 ? `${count} rule(s) configured` : "None";
      }
      default:
        return "Not configured";
    }
  };

  // Replacement Rules API operations
  const addReplacementMutation = useMutation({
    mutationFn: (payload: ReplacementRulePayload) => 
      rulesApi.createReplacementRule(id!, payload),
    onSuccess: () => {
      toast.success("Replacement rule added.");
      refetchReplacements();
      setNewRepRule({ search_text: "", replacement_text: "", match_mode: "literal", is_active: true });
    },
    onError: (err: any) => {
      toast.error(`Failed to add: ${err.message}`);
    }
  });

  const updateReplacementMutation = useMutation({
    mutationFn: (payload: ReplacementRulePayload) => 
      rulesApi.updateReplacementRule(id!, editingRepId!, payload),
    onSuccess: () => {
      toast.success("Replacement rule updated.");
      refetchReplacements();
      setEditingRepId(null);
    },
    onError: (err: any) => {
      toast.error(`Failed to save: ${err.message}`);
    }
  });

  const deleteReplacementMutation = useMutation({
    mutationFn: (repId: string) => 
      rulesApi.deleteReplacementRule(id!, repId),
    onSuccess: () => {
      toast.success("Replacement rule deleted.");
      refetchReplacements();
    },
    onError: (err: any) => {
      toast.error(`Failed to delete: ${err.message}`);
    }
  });

  // Render Skeletons for edits loading
  if (isRuleLoading) {
    return (
      <div className="flex flex-col gap-6 select-none max-w-3xl mx-auto w-full animate-pulse mt-4">
        <div className="h-6 bg-muted rounded w-1/4"></div>
        <div className="h-8 bg-muted rounded w-1/2"></div>
        <div className="flex flex-col gap-4 mt-8">
          {[1, 2, 3, 4].map(n => (
            <div key={n} className="h-16 bg-muted rounded-lg w-full"></div>
          ))}
        </div>
      </div>
    );
  }

  if (isRuleError) {
    return (
      <div className="p-8 flex flex-col items-center justify-center gap-3 border border-error-border bg-error-bg text-error max-w-xl mx-auto mt-12 rounded-lg">
        <span className="text-sm font-bold">Failed to load forwarding rule details.</span>
        <Button onClick={() => navigate("/forwards")} variant="outline" size="sm">
          Go Back
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 max-w-4xl mx-auto w-full pb-16 select-none animate-fade-in">
      {/* Activation Banner */}
      {!isNewRule && ruleData && !ruleData.is_active && (
        <ActivationBanner 
          isActive={false} 
          onActivate={() => activateMutation.mutate()} 
          isLoading={activateMutation.isPending}
        />
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border pb-3.5 gap-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            {isNewRule ? "Create Forward" : "Edit Forward"}
          </h1>
          <p className="text-xs text-muted-foreground">
            Configure rules, filters, attributes, and text modifications.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => navigate("/forwards")} variant="outline" size="sm">
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={createRuleMutation.isPending || updateRuleMutation.isPending}
            className="flex items-center gap-1.5"
            size="sm"
          >
            {(createRuleMutation.isPending || updateRuleMutation.isPending) ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            <span>Save Rule</span>
          </Button>
        </div>
      </div>

      {/* Accordion Panels */}
      <div className="flex flex-col gap-3.5 mt-1">
        {/* PANEL 1: Basic Config */}
        <CollapsiblePanel 
          title="1. Basic Config" 
          summary={getPanelSummary("basic")}
          isOpen={activePanels.has("basic")}
          onToggle={() => togglePanel("basic")}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="source_id" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                Source Channel
              </label>
              <select
                id="source_id"
                value={formData.source_id}
                onChange={(e) => setFormData(prev => ({ ...prev, source_id: e.target.value }))}
                className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
              >
                <option value="">Select a telegram source...</option>
                {sourcesData?.items.map(src => (
                  <option key={src.id} value={src.id}>
                    {src.display_name} {src.telegram_username ? `(@${src.telegram_username})` : `(${src.telegram_id})`}
                  </option>
                ))}
              </select>
              {apiErrors["source_id"] && (
                <p className="text-error text-xs mt-1 font-semibold">{apiErrors["source_id"]}</p>
              )}
            </div>

            <div>
              <label htmlFor="destination_channel" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                Destination Channel
              </label>
              <input
                id="destination_channel"
                type="text"
                value={formData.destination_channel}
                onChange={(e) => setFormData(prev => ({ ...prev, destination_channel: e.target.value }))}
                placeholder="e.g. @my_destination_channel or -100123456789"
                className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
              />
              {apiErrors["destination_channel"] && (
                <p className="text-error text-xs mt-1 font-semibold">{apiErrors["destination_channel"]}</p>
              )}
            </div>

            {/* Media Type Checkboxes */}
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                Media Filters (Allow)
              </label>
              <div className="flex gap-4">
                {["text", "photo"].map(type => {
                  const checked = formData.media_type_filter.includes(type);
                  return (
                    <label key={type} className="inline-flex items-center gap-2 text-sm font-semibold select-none cursor-pointer">
                      <input 
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          const next = checked 
                            ? formData.media_type_filter.filter(t => t !== type)
                            : [...formData.media_type_filter, type];
                          setFormData(prev => ({ ...prev, media_type_filter: next }));
                        }}
                        className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                      />
                      <span className="capitalize">{type}</span>
                    </label>
                  );
                })}
              </div>
              {apiErrors["media_type_filter"] && (
                <p className="text-error text-xs mt-1 font-semibold">{apiErrors["media_type_filter"]}</p>
              )}
            </div>

            <div className="md:col-span-2 flex items-center gap-2 mt-2">
              <input 
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
              />
              <label htmlFor="is_active" className="text-sm font-bold text-foreground select-none cursor-pointer">
                Rule Enabled / Active
              </label>
            </div>
          </div>
        </CollapsiblePanel>

        {/* PANEL 2: Time Window */}
        <CollapsiblePanel 
          title="2. Time Window" 
          summary={getPanelSummary("time")}
          isOpen={activePanels.has("time")}
          onToggle={() => togglePanel("time")}
        >
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <input 
                type="checkbox"
                id="time_enabled"
                checked={formData.time_window !== null}
                onChange={(e) => {
                  if (e.target.checked) {
                    setFormData(prev => ({
                      ...prev,
                      time_window: {
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Warsaw",
                        days_of_week: ["MON", "TUE", "WED", "THU", "FRI"],
                        start_time: "09:00",
                        end_time: "17:00"
                      }
                    }));
                  } else {
                    setFormData(prev => ({ ...prev, time_window: null }));
                  }
                }}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
              />
              <label htmlFor="time_enabled" className="text-sm font-bold text-foreground select-none cursor-pointer">
                Restrict forwarding to specific days/hours
              </label>
            </div>

            {formData.time_window && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border border-border p-4 bg-muted-bg/30 rounded-lg animate-in fade-in slide-in-from-top-1 duration-200">
                <div className="md:col-span-3">
                  <label className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                    Days of Week
                  </label>
                  <div className="flex flex-wrap gap-3">
                    {["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"].map(day => {
                      const checked = formData.time_window!.days_of_week.includes(day);
                      return (
                        <label key={day} className="inline-flex items-center gap-1.5 text-xs font-bold select-none cursor-pointer">
                          <input 
                            type="checkbox"
                            checked={checked}
                            onChange={() => {
                              const current = formData.time_window!.days_of_week;
                              const next = checked 
                                ? current.filter(d => d !== day)
                                : [...current, day];
                              setFormData(prev => ({
                                ...prev,
                                time_window: { ...prev.time_window!, days_of_week: next }
                              }));
                            }}
                            className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-primary"
                          />
                          <span>{day}</span>
                        </label>
                      );
                    })}
                  </div>
                  {apiErrors["time_window.days_of_week"] && (
                    <p className="text-error text-xs mt-1 font-semibold">{apiErrors["time_window.days_of_week"]}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="tz" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                    Timezone
                  </label>
                  <input
                    id="tz"
                    type="text"
                    value={formData.time_window.timezone}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      time_window: { ...prev.time_window!, timezone: e.target.value }
                    }))}
                    placeholder="e.g. Europe/Warsaw"
                    className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                  />
                  {apiErrors["time_window.timezone"] && (
                    <p className="text-error text-xs mt-1 font-semibold">{apiErrors["time_window.timezone"]}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="start_time" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                    Start Time
                  </label>
                  <input
                    id="start_time"
                    type="time"
                    value={formData.time_window.start_time}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      time_window: { ...prev.time_window!, start_time: e.target.value }
                    }))}
                    className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                  />
                  {apiErrors["time_window.start_time"] && (
                    <p className="text-error text-xs mt-1 font-semibold">{apiErrors["time_window.start_time"]}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="end_time" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                    End Time
                  </label>
                  <input
                    id="end_time"
                    type="time"
                    value={formData.time_window.end_time}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      time_window: { ...prev.time_window!, end_time: e.target.value }
                    }))}
                    className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                  />
                  {apiErrors["time_window.end_time"] && (
                    <p className="text-error text-xs mt-1 font-semibold">{apiErrors["time_window.end_time"]}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </CollapsiblePanel>

        {/* PANEL 3: Sampling */}
        <CollapsiblePanel 
          title="3. Sampling" 
          summary={getPanelSummary("sampling")}
          isOpen={activePanels.has("sampling")}
          onToggle={() => togglePanel("sampling")}
        >
          <div className="max-w-xs">
            <label htmlFor="sampling_n" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
              Forward Every Nth Message
            </label>
            <input
              id="sampling_n"
              type="number"
              min="1"
              value={formData.sampling.n}
              onChange={(e) => {
                const val = parseInt(e.target.value) || 1;
                setFormData(prev => ({ ...prev, sampling: { n: val } }));
              }}
              className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
            />
            <p className="text-xs text-muted-foreground font-medium mt-1">
              Set to 1 to forward all matched messages. Set to 2 to forward every second message, etc.
            </p>
            {apiErrors["sampling.n"] && (
              <p className="text-error text-xs mt-1 font-semibold">{apiErrors["sampling.n"]}</p>
            )}
          </div>
        </CollapsiblePanel>

        {/* PANEL 4: Keyword Filters */}
        <CollapsiblePanel 
          title="4. Keyword Filters" 
          summary={getPanelSummary("keywords")}
          isOpen={activePanels.has("keywords")}
          onToggle={() => togglePanel("keywords")}
        >
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2">
                Match Mode
              </label>
              <div className="flex gap-4">
                {["literal", "regex"].map((mode) => (
                  <label key={mode} className="inline-flex items-center gap-1.5 text-sm font-semibold select-none cursor-pointer">
                    <input 
                      type="radio"
                      name="keyword_match_mode"
                      value={mode}
                      checked={formData.keyword_match_mode === mode}
                      onChange={(e) => setFormData(prev => ({ ...prev, keyword_match_mode: e.target.value as "literal" | "regex" }))}
                      className="w-4 h-4 border-border text-primary focus:ring-primary"
                    />
                    <span className="capitalize">{mode}</span>
                  </label>
                ))}
              </div>
              {apiErrors["keyword_match_mode"] && (
                <p className="text-error text-xs mt-1 font-semibold">{apiErrors["keyword_match_mode"]}</p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="block_keywords" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                  Block Keywords (One per line)
                </label>
                <textarea
                  id="block_keywords"
                  rows={4}
                  value={formData.block_keywords.join("\n")}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    block_keywords: e.target.value.split("\n").filter(Boolean)
                  }))}
                  placeholder="Block matching messages containing these..."
                  className="w-full p-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                />
                {apiErrors["block_keywords"] && (
                  <p className="text-error text-xs mt-1 font-semibold">{apiErrors["block_keywords"]}</p>
                )}
              </div>

              <div>
                <label htmlFor="allow_keywords" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                  Allow Keywords (One per line)
                </label>
                <textarea
                  id="allow_keywords"
                  rows={4}
                  value={formData.allow_keywords.join("\n")}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    allow_keywords: e.target.value.split("\n").filter(Boolean)
                  }))}
                  placeholder="Only allow matching messages containing these..."
                  className="w-full p-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                />
                {apiErrors["allow_keywords"] && (
                  <p className="text-error text-xs mt-1 font-semibold">{apiErrors["allow_keywords"]}</p>
                )}
              </div>
            </div>
          </div>
        </CollapsiblePanel>

        {/* PANEL 5: Content Transforms */}
        <CollapsiblePanel 
          title="5. Content Transforms" 
          summary={getPanelSummary("transforms")}
          isOpen={activePanels.has("transforms")}
          onToggle={() => togglePanel("transforms")}
        >
          <div className="flex flex-col gap-6">
            {/* Text Simplification */}
            <div>
              <span className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2.5">
                Text Simplification
              </span>
              <div className="flex flex-wrap gap-4">
                <label className="inline-flex items-center gap-2 text-sm font-semibold select-none cursor-pointer">
                  <input 
                    type="checkbox"
                    checked={formData.remove_links}
                    onChange={(e) => setFormData(prev => ({ ...prev, remove_links: e.target.checked }))}
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>Remove Links</span>
                </label>
                <label className="inline-flex items-center gap-2 text-sm font-semibold select-none cursor-pointer">
                  <input 
                    type="checkbox"
                    checked={formData.remove_hashtags}
                    onChange={(e) => setFormData(prev => ({ ...prev, remove_hashtags: e.target.checked }))}
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>Remove Hashtags</span>
                </label>
                <label className="inline-flex items-center gap-2 text-sm font-semibold select-none cursor-pointer">
                  <input 
                    type="checkbox"
                    checked={formData.remove_mentions}
                    onChange={(e) => setFormData(prev => ({ ...prev, remove_mentions: e.target.checked }))}
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>Remove Mentions</span>
                </label>
              </div>
            </div>

            <div className="h-px bg-border" />

            {/* Media Handling */}
            <div>
              <span className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2.5">
                Media Handling
              </span>
              <div className="flex gap-4">
                {["forward", "ignore", "caption_only"].map(mode => (
                  <label key={mode} className="inline-flex items-center gap-1.5 text-sm font-semibold select-none cursor-pointer">
                    <input 
                      type="radio"
                      name="forward_media"
                      value={mode}
                      checked={formData.forward_media === mode}
                      onChange={(e) => setFormData(prev => ({ ...prev, forward_media: e.target.value as "forward" | "ignore" | "caption_only" }))}
                      className="w-4 h-4 border-border text-primary focus:ring-primary"
                    />
                    <span className="capitalize">{mode.replace("_", " ")}</span>
                  </label>
                ))}
              </div>
              {apiErrors["forward_media"] && (
                <p className="text-error text-xs mt-1 font-semibold">{apiErrors["forward_media"]}</p>
              )}
            </div>

            {/* Media Replacement section (Shown conditionally) */}
            {(formData.forward_media === "forward" || formData.forward_media === "caption_only") && (
              <div className="border border-border p-4 bg-muted-bg/30 rounded-lg animate-in fade-in duration-200 flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <input 
                    type="checkbox"
                    id="media_rep_enabled"
                    checked={formData.media_replacement.enabled}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      media_replacement: { ...prev.media_replacement, enabled: e.target.checked }
                    }))}
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                  />
                  <label htmlFor="media_rep_enabled" className="text-sm font-bold text-foreground select-none cursor-pointer">
                    Enable Media Replacement Image
                  </label>
                </div>

                {formData.media_replacement.enabled && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in duration-200">
                    <div>
                      <label htmlFor="media_replacement_path" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                        Replacement Image Path / Filename
                      </label>
                      <div className="flex gap-2">
                        <input
                          id="media_replacement_path"
                          type="text"
                          value={formData.media_replacement.replacement_image_path || ""}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            media_replacement: { ...prev.media_replacement, replacement_image_path: e.target.value || null }
                          }))}
                          placeholder="Browse folder or type filename..."
                          className="flex-grow h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                        />
                        <Button 
                          type="button" 
                          variant="outline" 
                          onClick={() => setShowImageBrowser(true)}
                          className="flex items-center gap-1.5 shrink-0"
                        >
                          <FolderOpen className="w-4 h-4" />
                          <span>Browse</span>
                        </Button>
                      </div>
                      {apiErrors["media_replacement.replacement_image_path"] && (
                        <p className="text-error text-xs mt-1 font-semibold">{apiErrors["media_replacement.replacement_image_path"]}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                        Caption Mode for Replacement
                      </label>
                      <div className="flex flex-col gap-2 mt-2">
                        {[
                          { val: "use_replacement", label: "Use Replacement Image caption" },
                          { val: "use_source", label: "Preserve original source caption" },
                          { val: "none", label: "Clear caption (send image empty)" }
                        ].map(cMode => (
                          <label key={cMode.val} className="inline-flex items-center gap-1.5 text-xs font-bold select-none cursor-pointer">
                            <input 
                              type="radio"
                              name="replacement_caption_mode"
                              value={cMode.val}
                              checked={formData.media_replacement.replacement_caption_mode === cMode.val}
                              onChange={() => setFormData(prev => ({
                                ...prev,
                                media_replacement: { ...prev.media_replacement, replacement_caption_mode: cMode.val as any }
                              }))}
                              className="w-3.5 h-3.5 border-border text-primary focus:ring-primary"
                            />
                            <span>{cMode.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="h-px bg-border" />

            {/* Source references auto-replacement */}
            <div className="border border-border p-4 bg-muted-bg/30 rounded-lg flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <input 
                  type="checkbox"
                  id="auto_refs_enabled"
                  checked={formData.auto_replace_source_refs.enabled}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    auto_replace_source_refs: { ...prev.auto_replace_source_refs, enabled: e.target.checked }
                  }))}
                  className="w-4 h-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                />
                <label htmlFor="auto_refs_enabled" className="text-sm font-bold text-foreground select-none cursor-pointer">
                  Auto-Replace Source Handle References
                </label>
              </div>

              {formData.auto_replace_source_refs.enabled && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in duration-200">
                  <div>
                    <label htmlFor="refs_replacement" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                      Replacement handle/link
                    </label>
                    <input
                      id="refs_replacement"
                      type="text"
                      value={formData.auto_replace_source_refs.replacement || ""}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        auto_replace_source_refs: { ...prev.auto_replace_source_refs, replacement: e.target.value || null }
                      }))}
                      placeholder="e.g. @my_destination_handle"
                      className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                    />
                    {apiErrors["auto_replace_source_refs.replacement"] && (
                      <p className="text-error text-xs mt-1 font-semibold">{apiErrors["auto_replace_source_refs.replacement"]}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 md:pt-6">
                    <input 
                      type="checkbox"
                      id="refs_replace_display"
                      checked={formData.auto_replace_source_refs.replace_display_name}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        auto_replace_source_refs: { ...prev.auto_replace_source_refs, replace_display_name: e.target.checked }
                      }))}
                      className="w-4 h-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                    />
                    <label htmlFor="refs_replace_display" className="text-xs font-bold text-foreground select-none cursor-pointer uppercase tracking-wider">
                      Replace Text Channel Title References
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </CollapsiblePanel>

        {/* PANEL 6: Attribution */}
        <CollapsiblePanel 
          title="6. Attribution" 
          summary={getPanelSummary("attribution")}
          isOpen={activePanels.has("attribution")}
          onToggle={() => togglePanel("attribution")}
        >
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <input 
                type="checkbox"
                id="att_enabled"
                checked={formData.attribution.enabled}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  attribution: { ...prev.attribution, enabled: e.target.checked }
                }))}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
              />
              <label htmlFor="att_enabled" className="text-sm font-bold text-foreground select-none cursor-pointer">
                Append attribution header/footer to forwarded messages
              </label>
            </div>

            {formData.attribution.enabled && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border border-border p-4 bg-muted-bg/30 rounded-lg animate-in fade-in duration-200">
                <div>
                  <label className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2">
                    Attribution Position
                  </label>
                  <div className="flex gap-4">
                    {["prefix", "suffix"].map(pos => (
                      <label key={pos} className="inline-flex items-center gap-1.5 text-sm font-semibold select-none cursor-pointer">
                        <input 
                          type="radio"
                          name="att_position"
                          value={pos}
                          checked={formData.attribution.position === pos}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            attribution: { ...prev.attribution, position: e.target.value as "prefix" | "suffix" }
                          }))}
                          className="w-4 h-4 border-border text-primary focus:ring-primary"
                        />
                        <span className="capitalize">{pos}</span>
                      </label>
                    ))}
                  </div>
                  {apiErrors["attribution.position"] && (
                    <p className="text-error text-xs mt-1 font-semibold">{apiErrors["attribution.position"]}</p>
                  )}
                </div>

                <div className="md:col-span-2">
                  <label htmlFor="att_format" className="block text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1.5">
                    Attribution Format Template
                  </label>
                  <input
                    id="att_format"
                    type="text"
                    ref={attributionFormatInputRef}
                    value={formData.attribution.format}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      attribution: { ...prev.attribution, format: e.target.value }
                    }))}
                    className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary focus:border-primary text-sm font-medium"
                  />
                  {/* Chip Tokens */}
                  <div className="flex gap-2 mt-2 items-center flex-wrap select-none">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide">
                      Click to insert:
                    </span>
                    <button
                      type="button"
                      onClick={() => handleInsertToken("{source_name}")}
                      className="px-2.5 py-1 bg-muted hover:bg-border border border-border text-foreground font-semibold text-[10px] rounded-md transition-colors cursor-pointer select-none"
                    >
                      {"{source_name}"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleInsertToken("{source_username}")}
                      className="px-2.5 py-1 bg-muted hover:bg-border border border-border text-foreground font-semibold text-[10px] rounded-md transition-colors cursor-pointer select-none"
                    >
                      {"{source_username}"}
                    </button>
                  </div>
                  {apiErrors["attribution.format"] && (
                    <p className="text-error text-xs mt-1 font-semibold">{apiErrors["attribution.format"]}</p>
                  )}

                  {/* Live Preview */}
                  {attributionPreview && (
                    <div className="mt-4 border-l-4 border-primary pl-3 py-1 bg-muted-bg/30 text-xs">
                      <span className="font-bold text-muted-foreground uppercase tracking-wide text-[9px] block mb-0.5">
                        Live Preview ({formData.attribution.position})
                      </span>
                      <p className="text-foreground italic font-medium">
                        {attributionPreview}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </CollapsiblePanel>

        {/* PANEL 7: Replacement Rules */}
        <CollapsiblePanel 
          title="7. Replacement Rules" 
          summary={getPanelSummary("replacements")}
          isOpen={activePanels.has("replacements")}
          onToggle={() => togglePanel("replacements")}
        >
          {isNewRule ? (
            <div className="flex items-center gap-2 p-3 bg-muted border border-border rounded-lg text-muted-foreground text-sm font-semibold select-none">
              <Info className="w-4 h-4 text-primary shrink-0" />
              <span>Save the forwarding rule first to configure text replacement rules.</span>
            </div>
          ) : (
            <div className="flex flex-col gap-4 select-none">
              {/* Inline list of replacement rules */}
              <div className="border border-border rounded-lg bg-card overflow-hidden">
                <table className="w-full text-left border-collapse text-xs md:text-sm font-medium">
                  <thead>
                    <tr className="border-b border-border bg-muted-bg text-muted-foreground font-bold uppercase tracking-wider text-[11px]">
                      <th className="py-2.5 px-3">Search Text</th>
                      <th className="py-2.5 px-3">Replacement</th>
                      <th className="py-2.5 px-3 w-24">Match Mode</th>
                      <th className="py-2.5 px-3 w-16 text-center">Active</th>
                      <th className="py-2.5 px-3 w-28 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {/* Add Inline Row */}
                    <tr className="bg-primary/5">
                      <td className="py-2 px-3">
                        <input
                          type="text"
                          value={newRepRule.search_text}
                          onChange={(e) => setNewRepRule(prev => ({ ...prev, search_text: e.target.value }))}
                          placeholder="e.g. hello"
                          className="w-full h-8 px-2 border border-border rounded-md bg-card text-xs focus:ring-primary"
                        />
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="text"
                          value={newRepRule.replacement_text}
                          onChange={(e) => setNewRepRule(prev => ({ ...prev, replacement_text: e.target.value }))}
                          placeholder="e.g. hi"
                          className="w-full h-8 px-2 border border-border rounded-md bg-card text-xs focus:ring-primary"
                        />
                      </td>
                      <td className="py-2 px-3">
                        <select
                          value={newRepRule.match_mode}
                          onChange={(e) => setNewRepRule(prev => ({ ...prev, match_mode: e.target.value as any }))}
                          className="w-full h-8 px-1.5 border border-border rounded-md bg-card text-xs focus:ring-primary"
                        >
                          <option value="literal">Literal</option>
                          <option value="regex">Regex</option>
                        </select>
                      </td>
                      <td className="py-2 px-3 text-center">
                        <input
                          type="checkbox"
                          checked={newRepRule.is_active}
                          onChange={(e) => setNewRepRule(prev => ({ ...prev, is_active: e.target.checked }))}
                          className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-primary cursor-pointer"
                        />
                      </td>
                      <td className="py-2 px-3 text-center">
                        <Button 
                          type="button" 
                          size="sm" 
                          onClick={() => addReplacementMutation.mutate(newRepRule)}
                          disabled={!newRepRule.search_text || addReplacementMutation.isPending}
                          className="h-8 py-1 px-3 flex items-center gap-1.5 w-full justify-center"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          <span>Add</span>
                        </Button>
                      </td>
                    </tr>

                    {/* Rules list */}
                    {!replacementsData?.items || replacementsData.items.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground italic text-xs">
                          No text replacements configured yet.
                        </td>
                      </tr>
                    ) : (
                      replacementsData.items.map((rep) => {
                        const isEditing = editingRepId === rep.id;

                        if (isEditing) {
                          return (
                            <tr key={rep.id} className="bg-warning-bg/10">
                              <td className="py-2 px-3">
                                <input
                                  type="text"
                                  value={editingRepData.search_text}
                                  onChange={(e) => setEditingRepData(prev => ({ ...prev, search_text: e.target.value }))}
                                  className="w-full h-8 px-2 border border-border rounded-md bg-card text-xs focus:ring-primary"
                                />
                              </td>
                              <td className="py-2 px-3">
                                <input
                                  type="text"
                                  value={editingRepData.replacement_text}
                                  onChange={(e) => setEditingRepData(prev => ({ ...prev, replacement_text: e.target.value }))}
                                  className="w-full h-8 px-2 border border-border rounded-md bg-card text-xs focus:ring-primary"
                                />
                              </td>
                              <td className="py-2 px-3">
                                <select
                                  value={editingRepData.match_mode}
                                  onChange={(e) => setEditingRepData(prev => ({ ...prev, match_mode: e.target.value as any }))}
                                  className="w-full h-8 px-1.5 border border-border rounded-md bg-card text-xs focus:ring-primary"
                                >
                                  <option value="literal">Literal</option>
                                  <option value="regex">Regex</option>
                                </select>
                              </td>
                              <td className="py-2 px-3 text-center">
                                <input
                                  type="checkbox"
                                  checked={editingRepData.is_active}
                                  onChange={(e) => setEditingRepData(prev => ({ ...prev, is_active: e.target.checked }))}
                                  className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-primary cursor-pointer"
                                />
                              </td>
                              <td className="py-2 px-3">
                                <div className="flex gap-1.5 justify-center">
                                  <Button 
                                    size="sm"
                                    onClick={() => updateReplacementMutation.mutate(editingRepData)}
                                    disabled={updateReplacementMutation.isPending}
                                    className="h-8 px-2.5 text-xs bg-success text-white hover:bg-success-border font-bold shadow-3xs"
                                  >
                                    Save
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => setEditingRepId(null)}
                                    className="h-8 px-2 text-xs font-semibold"
                                  >
                                    Cancel
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        }

                        return (
                          <tr key={rep.id} className="hover:bg-muted-bg/30">
                            <td className="py-2.5 px-3 font-mono font-bold text-foreground">
                              {rep.search_text}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-muted-foreground">
                              {rep.replacement_text}
                            </td>
                            <td className="py-2.5 px-3 font-semibold capitalize text-xs">
                              {rep.match_mode}
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <span className={cn(
                                "inline-block w-2.5 h-2.5 rounded-full",
                                rep.is_active ? "bg-primary" : "bg-muted"
                              )} />
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="flex items-center justify-center gap-2">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingRepId(rep.id);
                                    setEditingRepData({
                                      search_text: rep.search_text,
                                      replacement_text: rep.replacement_text,
                                      match_mode: rep.match_mode,
                                      is_active: rep.is_active,
                                    });
                                  }}
                                  className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted"
                                >
                                  <Edit className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    if (confirm("Delete this text replacement rule?")) {
                                      deleteReplacementMutation.mutate(rep.id);
                                    }
                                  }}
                                  className="p-1 rounded text-muted-foreground hover:text-error hover:bg-error-bg/60"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CollapsiblePanel>
      </div>

      {/* Media Gallery / Browse Modal Dialog */}
      {showImageBrowser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none">
          <div 
            className="fixed inset-0 bg-black/55 backdrop-blur-xs transition-opacity duration-200" 
            onClick={() => setShowImageBrowser(false)}
          />
          <div className="relative bg-card border border-border rounded-lg shadow-xl max-w-lg w-full p-6 flex flex-col max-h-[80vh] animate-in fade-in zoom-in-95 duration-200 z-10">
            <button
              onClick={() => setShowImageBrowser(false)}
              className="absolute right-4 top-4 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted"
            >
              <X className="w-4 h-4" />
            </button>
            <h3 className="text-lg font-bold text-foreground mb-4">
              Browse Replacement Images
            </h3>
            
            {/* Search filter input */}
            <input 
              type="text"
              value={imageSearch}
              onChange={(e) => setImageSearch(e.target.value)}
              placeholder="Search images by name..."
              className="w-full h-10 px-3 border border-border rounded-md bg-card text-foreground focus:ring-primary text-sm font-medium mb-4 shrink-0"
            />

            <div className="flex-1 overflow-y-auto min-h-[200px] border border-border rounded-md bg-muted-bg/10 divide-y divide-border">
              {filteredImages.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground italic">
                  No matching image files found.
                </div>
              ) : (
                filteredImages.map((img) => (
                  <button
                    key={img}
                    type="button"
                    onClick={() => {
                      setFormData(prev => ({
                        ...prev,
                        media_replacement: {
                          ...prev.media_replacement,
                          replacement_image_path: img
                        }
                      }));
                      setShowImageBrowser(false);
                    }}
                    className="w-full py-3 px-4 text-left font-mono text-xs hover:bg-primary/5 hover:text-primary transition-colors cursor-pointer select-none text-foreground font-semibold flex items-center justify-between"
                  >
                    <span>{img}</span>
                    <Plus className="w-3.5 h-3.5 opacity-50" />
                  </button>
                ))
              )}
            </div>
            
            <div className="mt-4 flex justify-end shrink-0">
              <Button type="button" variant="outline" onClick={() => setShowImageBrowser(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
