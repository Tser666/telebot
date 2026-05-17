import { type ReactNode, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  FileText,
  History,
  LayoutDashboard,
  Package,
  PlusCircle,
  Sparkles,
} from "lucide-react";

import { getAICommandEnablementSummary, listCommandTemplates, listLLMProviders } from "@/api/commands";
import { listAccounts } from "@/api/accounts";
import { listRecentLLMUsage } from "@/api/llmUsage";
import { getSystemSettings } from "@/api/system";
import type { AccountSummary, CommandTemplateOut, LLMProviderOut } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CommandBadge } from "@/components/CommandBadge";
import { Glossary } from "@/components/ai/Glossary";
import { HowItWorks } from "@/components/ai/HowItWorks";
import { RecommendedSetup } from "@/components/ai/RecommendedSetup";
import { LLMProviders } from "@/pages/AI/LLMProviders";
import { RecentUsageContent } from "@/pages/AI/_components/RecentUsage";

type AITab = "overview" | "providers" | "usage";

const AI_TABS = new Set<AITab>(["overview", "providers", "usage"]);

function normalizeTab(tab: string | null): AITab {
  return tab && AI_TABS.has(tab as AITab) ? (tab as AITab) : "overview";
}

function providerLabel(p?: LLMProviderOut, modelOverride?: unknown) {
  if (!p) return "未选择";
  const model = typeof modelOverride === "string" && modelOverride.trim() ? modelOverride : p.default_model;
  return `${p.name} · ${model}`;
}

function commandModeLabel(template: CommandTemplateOut) {
  const mode = typeof template.config?.mode === "string" ? template.config.mode : "chat";
  const auto = template.config?.routing_mode === "auto";
  const search = template.config?.web_search === true;
  const parts = [mode, auto ? "auto" : "固定"];
  if (search || mode === "search") parts.push("联网");
  if (mode === "image" && template.config?.image_backend === "codex_image") parts.push("codex_image");
  return parts.join(" · ");
}

export function AIIndex() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [accountPickerOpen, setAccountPickerOpen] = useState(false);
  const activeTab = normalizeTab(searchParams.get("tab"));
  const providersQ = useQuery({
    queryKey: ["llm-providers"],
    queryFn: listLLMProviders,
  });
  const templatesQ = useQuery({
    queryKey: ["cmd-tpl"],
    queryFn: listCommandTemplates,
  });
  const settingsQ = useQuery({
    queryKey: ["system", "settings"],
    queryFn: getSystemSettings,
  });
  const usageQ = useQuery({
    queryKey: ["llm-usage", "recent", "summary"],
    queryFn: () => listRecentLLMUsage(20),
    retry: false,
    enabled: (providersQ.data?.length ?? 0) > 0,
  });
  const enablementQ = useQuery({
    queryKey: ["cmd-tpl", "ai-enablement-summary"],
    queryFn: getAICommandEnablementSummary,
    retry: false,
  });
  const accountsQ = useQuery({
    queryKey: ["accounts", "ai-enable-picker"],
    queryFn: listAccounts,
    enabled: false,
    retry: false,
  });

  const loading = providersQ.isLoading || templatesQ.isLoading;
  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Spinner className="text-primary" />
      </div>
    );
  }

  const providers = providersQ.data || [];
  const templates = templatesQ.data || [];
  const cmdPrefix = settingsQ.data?.command_prefix || ",";
  const providerById = new Map(providers.map((p) => [p.id, p]));
  const aiTemplates = templates.filter((t) => t.type === "ai");
  const providerCount = providers.length;
  const readyCount = providers.filter((p) => p.has_api_key || p.provider === "ollama").length;
  const usageSummary = usageQ.data?.summary;
  const enablementSummary = enablementQ.data;
  const enabledAccountCount = enablementSummary?.enabled_accounts ?? 0;
  const totalAccountCount = enablementSummary?.total_accounts ?? 0;
  const accountChoices = accountsQ.data ?? [];

  const goAccountCommands = (accountId: number) => {
    navigate(`/accounts/${accountId}?tab=commands`);
  };

  const handleEnableCommand = async () => {
    const result = await accountsQ.refetch();
    const accounts = result.data ?? [];
    if (accounts.length === 0) {
      navigate("/accounts");
      return;
    }
    if (accounts.length === 1) {
      goAccountCommands(accounts[0].id);
      return;
    }
    setAccountPickerOpen(true);
  };

  if (activeTab === "providers") {
    return (
      <div className="space-y-6">
        <AIHeader />
        <Subnav activeTab={activeTab} />
        <div className="rounded-md border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          已配置 {providerCount} 个模型提供商，其中 {readyCount} 个可调用。联网搜索需要 api_format=responses 的 OpenAI provider。
        </div>
        <LLMProviders />
      </div>
    );
  }

  if (activeTab === "usage") {
    return (
      <div className="space-y-6">
        <AIHeader />
        <Subnav activeTab={activeTab} />
        <RecentUsageContent />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <AIHeader />
      <Subnav activeTab={activeTab} />

      <div className="grid gap-3 md:grid-cols-3">
        <StatusCard
          icon={Package}
          label="Provider 就绪"
          value={`${readyCount}/${providerCount}`}
          hint={providerCount > 0 ? "已可调用 / 总数" : "先添加一个模型提供商"}
          ready={readyCount > 0}
        />
        <StatusCard
          icon={Bot}
          label="AI 命令数"
          value={aiTemplates.length}
          hint={aiTemplates.length > 0 ? "type=ai 模板" : "创建第一条 AI 命令模板"}
          ready={aiTemplates.length > 0}
        />
        <StatusCard
          icon={History}
          label="最近 20 次"
          value={usageSummary ? `${usageSummary.request_count} 次 / 失败 ${usageSummary.failed_count}` : "暂无"}
          hint={usageSummary ? `平均耗时 ${usageSummary.avg_latency_ms}ms` : usageQ.isError ? "调用摘要暂不可用" : "触发调用后展示摘要"}
          ready={(usageSummary?.request_count ?? 0) > 0}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">三步走</CardTitle>
          <CardDescription>按顺序完成后，你的 Telegram 账号就能用 AI 命令回复消息。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-3">
          <SetupStep
            no="1"
            title="添加模型提供商"
            desc="配置 OpenAI、Anthropic、Ollama 或兼容接口，确认至少一个模型可调用。"
            done={providerCount > 0}
            action="去配置"
            href="/ai?tab=providers&newProvider=1"
          />
          <SetupStep
            no="2"
            title="创建一条 AI 命令"
            desc={<>建议先建 <CommandBadge>{cmdPrefix}ai</CommandBadge>，绑定默认模型或开启 auto 路由。</>}
            done={aiTemplates.length > 0}
            action="去创建"
            href="/plugins/templates?new=ai&returnTo=/ai"
          />
          <SetupStep
            no="3"
            title="在账号上启用命令"
            desc={
              totalAccountCount > 0
                ? `已有 ${enabledAccountCount}/${totalAccountCount} 个账号启用了至少一条 AI 命令。`
                : "还没有账号；创建账号后到账号详情的命令 tab 勾选模板。"
            }
            done={enabledAccountCount > 0}
            action="去启用"
            onAction={handleEnableCommand}
            actionLoading={accountsQ.isFetching}
          />
        </CardContent>
      </Card>

      <Dialog open={accountPickerOpen} onOpenChange={setAccountPickerOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>选择要启用 AI 命令的账号</DialogTitle>
            <DialogDescription>
              将跳转到账号详情的命令 Tab，你可以在那里勾选要启用的 AI 命令模板。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            {accountChoices.map((account) => (
              <Button
                key={account.id}
                type="button"
                variant="outline"
                className="h-auto justify-between gap-3 px-3 py-2 text-left"
                onClick={() => goAccountCommands(account.id)}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">{accountDisplayName(account)}</span>
                  <span className="block truncate text-xs text-muted-foreground">{account.phone}</span>
                </span>
                <ArrowRight className="h-4 w-4 shrink-0" />
              </Button>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">你的 AI 命令</CardTitle>
          <CardDescription>展示 type=ai 的命令模板；编辑会带 returnTo=/ai 回到总览。</CardDescription>
        </CardHeader>
        <CardContent>
          {aiTemplates.length === 0 ? (
            <div className="rounded-md border border-dashed py-8 text-center">
              <p className="text-sm text-muted-foreground">还没有 AI 命令模板。</p>
              <Button asChild className="mt-3" size="sm">
                <Link to="/plugins/templates?new=ai&returnTo=/ai">
                  <PlusCircle className="mr-1 h-4 w-4" />
                  创建 AI 命令
                </Link>
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>命令</TableHead>
                  <TableHead>模型</TableHead>
                  <TableHead>模式</TableHead>
                  <TableHead>说明</TableHead>
                  <TableHead className="w-24">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {aiTemplates.map((template) => {
                  const provider = providerById.get(Number(template.config?.provider_id));
                  const modelText =
                    template.config?.mode === "image" && template.config?.image_backend === "codex_image"
                      ? "codex_image 插件"
                      : providerLabel(provider, template.config?.model);
                  return (
                    <TableRow key={template.id}>
                      <TableCell className="font-mono">{cmdPrefix}{template.name}</TableCell>
                      <TableCell>{modelText}</TableCell>
                      <TableCell>
                        <Badge variant={template.config?.routing_mode === "auto" ? "success" : "secondary"}>
                          {commandModeLabel(template)}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[22rem] truncate text-sm text-muted-foreground">
                        {template.description || "未填写说明"}
                      </TableCell>
                      <TableCell>
                        <Button asChild variant="outline" size="sm">
                          <Link to={`/plugins/templates?edit=${template.id}&returnTo=${encodeURIComponent("/ai")}`}>
                            编辑
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        <HowItWorks cmdPrefix={cmdPrefix} defaultOpen={location.hash === "#how-it-works"} />
        <RecommendedSetup cmdPrefix={cmdPrefix} />
        <Glossary />
      </div>
    </div>
  );
}

function AIHeader() {
  return (
    <div>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI 命令中心</h1>
        <p className="text-sm text-muted-foreground">
          让你的 Telegram 账号回复变成 AI 助手。
        </p>
      </div>
    </div>
  );
}

function Subnav({ activeTab }: { activeTab: AITab }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button asChild variant={activeTab === "overview" ? "default" : "outline"} size="sm">
        <Link to="/ai">
          <LayoutDashboard className="mr-1 h-4 w-4" />
          总览
        </Link>
      </Button>
      <Button asChild variant={activeTab === "providers" ? "default" : "outline"} size="sm">
        <Link to="/ai?tab=providers">
          <Package className="mr-1 h-4 w-4" />
          模型提供商
        </Link>
      </Button>
      <Button asChild variant={activeTab === "usage" ? "default" : "outline"} size="sm">
        <Link to="/ai?tab=usage">
          <History className="mr-1 h-4 w-4" />
          最近调用
        </Link>
      </Button>
      <Button asChild variant="outline" size="sm">
        <Link to="/plugins/templates">
          <FileText className="mr-1 h-4 w-4" />
          已配置的命令
        </Link>
      </Button>
    </div>
  );
}

function StatusCard({
  icon: Icon,
  label,
  value,
  hint,
  ready,
}: {
  icon: typeof Package;
  label: string;
  value: string | number;
  hint: string;
  ready: boolean;
}) {
  return (
    <Card className={ready ? "border-emerald-500/40 bg-emerald-500/5" : undefined}>
      <CardHeader className="pb-2">
        <CardDescription className="inline-flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {label}
        </CardDescription>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{hint}</CardContent>
    </Card>
  );
}

function SetupStep({
  no,
  title,
  desc,
  done,
  action,
  href,
  onAction,
  actionLoading = false,
}: {
  no: string;
  title: string;
  desc: ReactNode;
  done: boolean;
  action: string;
  href?: string;
  onAction?: () => void | Promise<void>;
  actionLoading?: boolean;
}) {
  const actionContent = (
    <>
      {actionLoading ? "读取账号..." : action}
      <ArrowRight className="ml-1 h-4 w-4" />
    </>
  );
  return (
    <div className={done ? "rounded-md border border-emerald-500/40 bg-emerald-500/5 p-4" : "rounded-md border bg-background p-4"}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 font-medium">
          <span className="flex h-7 w-7 items-center justify-center rounded-full border text-xs">{no}</span>
          {title}
        </div>
        {done ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Sparkles className="h-4 w-4 text-muted-foreground" />}
      </div>
      <p className="mt-3 min-h-10 text-sm text-muted-foreground">{desc}</p>
      {href ? (
        <Button asChild variant={done ? "outline" : "default"} size="sm" className="mt-4">
          <Link to={href}>{actionContent}</Link>
        </Button>
      ) : (
        <Button
          type="button"
          variant={done ? "outline" : "default"}
          size="sm"
          className="mt-4"
          disabled={actionLoading}
          onClick={onAction}
        >
          {actionContent}
        </Button>
      )}
    </div>
  );
}

function accountDisplayName(account: AccountSummary) {
  const name = account.display_name?.trim();
  const username = account.tg_username?.trim();
  if (name && username) return `${name} (@${username})`;
  if (name) return name;
  if (username) return `@${username}`;
  return `账号 #${account.id}`;
}
