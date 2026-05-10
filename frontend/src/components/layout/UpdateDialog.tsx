import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, RefreshCw, RotateCcw, CheckCircle2, AlertCircle } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { checkUpdate, pullUpdate, restartApp } from "@/api/system";
import type {
  CheckUpdateResult,
  PullUpdateResult,
} from "@/api/types";

type Step =
  | { kind: "checking" }
  | { kind: "up_to_date"; commit: string }
  | { kind: "has_update"; current: string; remote: string; ahead: number }
  | { kind: "pulling" }
  | { kind: "pulled"; newCommit: string | null; summary: string | null }
  | { kind: "pull_failed"; error: string }
  | { kind: "check_failed"; error: string }
  | { kind: "restarting"; countdown: number };

interface UpdateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function UpdateDialog({ open, onOpenChange }: UpdateDialogProps) {
  const [step, setStep] = useState<Step | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  // 打开时自动检查更新
  const doCheck = useCallback(async () => {
    setStep({ kind: "checking" });
    try {
      const res: CheckUpdateResult = await checkUpdate();
      if (res.error) {
        setStep({ kind: "check_failed", error: res.error });
      } else if (!res.has_update) {
        setStep({ kind: "up_to_date", commit: res.current_commit || "?" });
      } else {
        setStep({
          kind: "has_update",
          current: res.current_commit || "?",
          remote: res.remote_commit || "?",
          ahead: res.ahead,
        });
      }
    } catch (e) {
      setStep({
        kind: "check_failed",
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }, []);

  useEffect(() => {
    if (open) {
      doCheck();
    } else {
      setStep(null);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = undefined;
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = undefined;
      }
    };
  }, [open, doCheck]);

  const doPull = async () => {
    setStep({ kind: "pulling" });
    try {
      const res: PullUpdateResult = await pullUpdate();
      if (res.success) {
        setStep({ kind: "pulled", newCommit: res.new_commit, summary: res.summary });
      } else {
        setStep({ kind: "pull_failed", error: res.error || "未知错误" });
      }
    } catch (e) {
      setStep({
        kind: "pull_failed",
        error: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const doRestart = async () => {
    if (!window.confirm("确认重启应用？页面将在 5 秒后自动刷新。")) return;
    try {
      await restartApp();
      setStep({ kind: "restarting", countdown: 5 });
      let count = 5;
      timerRef.current = setInterval(() => {
        count -= 1;
        if (count <= 0) {
          if (timerRef.current) clearInterval(timerRef.current);
          window.location.reload();
        } else {
          setStep({ kind: "restarting", countdown: count });
        }
      }, 1000);
    } catch (e) {
      setStep({
        kind: "pull_failed",
        error: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const isActionable =
    step?.kind === "has_update" ||
    step?.kind === "pulled" ||
    step?.kind === "pull_failed" ||
    step?.kind === "check_failed";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>检查更新</DialogTitle>
          <DialogDescription>
            {step?.kind === "checking" && "正在检查远程仓库..."}
            {step?.kind === "up_to_date" && "当前已是最新版本"}
            {step?.kind === "has_update" && "发现新版本可用"}
            {step?.kind === "pulling" && "正在拉取代码..."}
            {step?.kind === "pulled" && "代码已拉取成功"}
            {step?.kind === "pull_failed" && "拉取失败"}
            {step?.kind === "check_failed" && "检查失败"}
            {step?.kind === "restarting" && "正在重启应用..."}
            {!step && "准备检查更新"}
          </DialogDescription>
        </DialogHeader>

        {/* 内容区 */}
        <div className="min-h-[80px]">
          {step?.kind === "checking" && (
            <div className="flex items-center gap-3 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">git fetch origin ...</span>
            </div>
          )}

          {step?.kind === "up_to_date" && (
            <div className="flex items-center gap-3 text-emerald-600 dark:text-emerald-300">
              <CheckCircle2 className="h-5 w-5" />
              <div className="text-sm space-y-1">
                <p>当前版本 <code className="bg-muted px-1 rounded">{step.commit}</code></p>
                <p className="text-muted-foreground">无需更新</p>
              </div>
            </div>
          )}

          {step?.kind === "has_update" && (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-amber-600 dark:text-amber-300">
                <AlertCircle className="h-5 w-5" />
                <span>远程有 {step.ahead} 个新 commit</span>
              </div>
              <div className="rounded-md bg-muted px-3 py-2 font-mono text-xs space-y-1">
                <p>当前: {step.current}</p>
                <p>远程: {step.remote}</p>
              </div>
            </div>
          )}

          {step?.kind === "pulling" && (
            <div className="flex items-center gap-3 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">git pull origin main ...</span>
            </div>
          )}

          {step?.kind === "pulled" && (
            <div className="flex items-center gap-3 text-emerald-600 dark:text-emerald-300">
              <CheckCircle2 className="h-5 w-5" />
              <div className="text-sm space-y-1">
                <p>已拉取到 <code className="bg-muted px-1 rounded">{step.newCommit}</code></p>
                {step.summary && (
                  <p className="text-muted-foreground">{step.summary}</p>
                )}
                <p className="text-amber-600 dark:text-amber-300">需要重启应用才能生效</p>
              </div>
            </div>
          )}

          {(step?.kind === "pull_failed" || step?.kind === "check_failed") && (
            <div className="flex items-start gap-3 text-destructive">
              <AlertCircle className="h-5 w-5 mt-0.5" />
              <div className="text-sm space-y-1">
                <p>错误信息：</p>
                <pre className="rounded bg-muted px-3 py-2 text-xs overflow-x-auto">
                  {step.error}
                </pre>
              </div>
            </div>
          )}

          {step?.kind === "restarting" && (
            <div className="flex items-center gap-3 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">
                正在重启，{step.countdown} 秒后自动刷新页面...
              </span>
            </div>
          )}
        </div>

        {/* 按钮区 */}
        {isActionable && (
          <DialogFooter className="gap-2">
            {(step?.kind === "check_failed" || step?.kind === "pull_failed") && (
              <Button variant="outline" size="sm" onClick={doCheck}>
                <RefreshCw className="mr-1 h-3.5 w-3.5" />
                重新检查
              </Button>
            )}
            {step?.kind === "has_update" && (
              <Button size="sm" onClick={doPull}>
                <RefreshCw className="mr-1 h-3.5 w-3.5" />
                拉取更新
              </Button>
            )}
            {step?.kind === "pulled" && (
              <>
                <Button variant="outline" size="sm" onClick={doCheck}>
                  再次检查
                </Button>
                <Button size="sm" onClick={doRestart}>
                  <RotateCcw className="mr-1 h-3.5 w-3.5" />
                  重启应用
                </Button>
              </>
            )}
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
