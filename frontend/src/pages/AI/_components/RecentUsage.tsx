import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, History } from "lucide-react";

import { listRecentLLMUsage } from "@/api/llmUsage";
import { listLLMProviders } from "@/api/commands";
import { getErrMsg } from "@/lib/api";
import { Spinner } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";
import { MetaBadge } from "@/components/ui/meta-badge";
import { MeterBar, SectionHeader, SignalPill, ToneRailCard } from "@/components/ui/status";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function RecentUsageContent() {
  const providersQ = useQuery({
    queryKey: ["llm-providers"],
    queryFn: listLLMProviders,
  });

  const providerCount = providersQ.data?.length ?? 0;
  const hasProviders = providerCount > 0;
  const usageQ = useQuery({
    queryKey: ["llm-usage", "recent", 100],
    queryFn: () => listRecentLLMUsage(100),
    retry: false,
    enabled: hasProviders,
  });

  if (providersQ.isLoading || (hasProviders && usageQ.isLoading)) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Spinner className="text-primary" />
      </div>
    );
  }

  if (providersQ.isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="inline-flex items-center gap-2">
            <History className="h-4 w-4" /> 近期调用
          </CardTitle>
          <CardDescription>暂时无法读取模型提供商：{getErrMsg(providersQ.error)}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (providerCount === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="inline-flex items-center gap-2">
            <History className="h-4 w-4" /> 近期调用
          </CardTitle>
          <CardDescription>先配置至少一个模型提供商，才会产生可查看的调用记录。</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/ai?tab=providers">
              前往配置模型提供商
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (usageQ.isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="inline-flex items-center gap-2">
            <History className="h-4 w-4" /> 近期调用
          </CardTitle>
          <CardDescription>暂时无法读取调用记录：{getErrMsg(usageQ.error)}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const usage = usageQ.data;
  const rows = usage?.items || [];
  const summary = usage?.summary;

  return (
    <Card>
      <CardHeader>
        <SectionHeader
          icon={History}
          title="近期调用"
          description="展示最近 100 条 LLM 调用记录与核心摘要。"
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {summary && (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <SignalPill tone="primary" label="请求数" value={summary.request_count} />
              <SignalPill tone="success" label="成功" value={summary.success_count} />
              <SignalPill tone={summary.failed_count > 0 ? "warn" : "neutral"} label="失败" value={summary.failed_count} />
              <SignalPill tone="neutral" label="Fallback" value={summary.fallback_count} />
              <SignalPill tone="neutral" label="总 Token" value={summary.total_tokens} />
              <SignalPill tone="primary" label="平均耗时" value={`${summary.avg_latency_ms}ms`} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <ToneRailCard
                icon={History}
                title="成功率"
                value={`${summary.request_count > 0 ? Math.round((summary.success_count / summary.request_count) * 100) : 0}%`}
                description={<MeterBar value={summary.request_count > 0 ? (summary.success_count / summary.request_count) * 100 : 0} tone={summary.failed_count > 0 ? "warn" : "success"} className="mt-2" />}
                tone={summary.failed_count > 0 ? "warn" : "success"}
              />
              <ToneRailCard
                icon={History}
                title="失败占比"
                value={`${summary.request_count > 0 ? Math.round((summary.failed_count / summary.request_count) * 100) : 0}%`}
                description={<MeterBar value={summary.request_count > 0 ? (summary.failed_count / summary.request_count) * 100 : 0} tone={summary.failed_count > 0 ? "warn" : "neutral"} className="mt-2" />}
                tone={summary.failed_count > 0 ? "warn" : "neutral"}
              />
              <ToneRailCard
                icon={History}
                title="Fallback 占比"
                value={`${summary.request_count > 0 ? Math.round((summary.fallback_count / summary.request_count) * 100) : 0}%`}
                description={<MeterBar value={summary.request_count > 0 ? (summary.fallback_count / summary.request_count) * 100 : 0} tone="primary" className="mt-2" />}
                tone="primary"
              />
            </div>
          </div>
        )}

        {rows.length === 0 ? (
          <p className="rounded-md border border-dashed py-8 text-center text-sm text-muted-foreground">
            暂无调用记录。触发一次 AI 指令后再回来查看。
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table className="min-w-[900px]">
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>模型提供商</TableHead>
                  <TableHead>模型</TableHead>
                  <TableHead>Token</TableHead>
                  <TableHead>耗时</TableHead>
                  <TableHead>结果</TableHead>
                  <TableHead>fallback</TableHead>
                  <TableHead>错误</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => {
                  const tokens = (r.input_tokens || 0) + (r.output_tokens || 0);
                  return (
                    <TableRow key={r.id}>
                      <TableCell className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleString()}</TableCell>
                      <TableCell className="font-mono text-xs">{r.source || "-"}</TableCell>
                      <TableCell>{r.provider_name || (r.provider_id ? `#${r.provider_id}` : "-")}</TableCell>
                      <TableCell className="font-mono text-xs">{r.model || "-"}</TableCell>
                      <TableCell>{tokens}</TableCell>
                      <TableCell>{r.latency_ms != null ? `${r.latency_ms}ms` : "-"}</TableCell>
                      <TableCell>
                        <MetaBadge tone={r.success ? "success" : "warn"}>{r.success ? "成功" : "失败"}</MetaBadge>
                      </TableCell>
                      <TableCell>{r.used_fallback ? "已使用" : "-"}</TableCell>
                      <TableCell className="font-mono text-xs">{r.error_type || "-"}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
