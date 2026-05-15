// 账号列表：卡片网格形式（移动端单列），含启停 / 详情 / 删除（二次确认）操作
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Bot, CheckCircle2, HelpCircle, Package, Plus, Power, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AccountSummaryCard } from "@/components/AccountSummaryCard";
import {
  deleteAccount,
  listAccounts,
  pauseAccount,
  resumeAccount,
} from "@/api/accounts";
import { getErrMsg } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const NEW_ACCOUNT_GUIDE_SEEN_KEY = "telebot.accounts.new_account_guide_seen.v1";

export function AccountList() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [guideOpen, setGuideOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: listAccounts,
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem(NEW_ACCOUNT_GUIDE_SEEN_KEY) === "1") return;
    setGuideOpen(true);
    localStorage.setItem(NEW_ACCOUNT_GUIDE_SEEN_KEY, "1");
  }, []);

  const toggleMut = useMutation({
    mutationFn: async (vars: { aid: number; pause: boolean }) =>
      vars.pause ? pauseAccount(vars.aid) : resumeAccount(vars.aid),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("已下发指令");
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  const delMut = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("已删除账号");
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">账号管理</h1>
          <p className="text-sm text-muted-foreground">
            每个账号 = 一个 session = 一个独立 worker 进程
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => setGuideOpen(true)}>
            <HelpCircle className="mr-1 h-4 w-4" /> 新手指引
          </Button>
          <Button onClick={() => nav("/accounts/new")}>
            <Plus className="mr-1 h-4 w-4" /> 新增账号
          </Button>
        </div>
      </div>

      <NewAccountGuideDialog
        open={guideOpen}
        onOpenChange={setGuideOpen}
        onCreate={() => {
          setGuideOpen(false);
          nav("/accounts/new");
        }}
      />

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <Spinner className="text-primary" />
        </div>
      ) : data && data.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.map((a) => (
            <AccountSummaryCard
              key={a.id}
              account={a}
              footer={
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>已启用 {a.enabled_features} 项</span>
                    <span title={formatDateTime(a.created_at)}>
                      {formatDateTime(a.created_at).slice(0, 10)}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-8 px-2"
                      onClick={() =>
                        toggleMut.mutate({
                          aid: a.id,
                          pause: a.status === "active",
                        })
                      }
                    >
                      <Power className="mr-1 h-3.5 w-3.5" />
                      {a.status === "active" ? "暂停" : "启动"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-8 px-2"
                      onClick={() => nav(`/accounts/${a.id}`)}
                    >
                      详情
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-8 px-2 text-destructive hover:text-destructive"
                      onClick={() => {
                        const label =
                          a.display_name ||
                          (a.tg_username ? `@${a.tg_username}` : `#${a.id}`);
                        if (
                          confirm(
                            `确认删除账号 ${label}？此操作会撤销 session 并清空配置。`,
                          )
                        )
                          delMut.mutate(a.id);
                      }}
                    >
                      <Trash2 className="mr-1 h-3.5 w-3.5" /> 删除
                    </Button>
                  </div>
                </div>
              }
            />
          ))}
        </div>
      ) : (
        <p className="rounded-lg border bg-card py-12 text-center text-sm text-muted-foreground">
          尚未绑定账号，
          <Link to="/accounts/new" className="text-primary hover:underline">
            立即新增
          </Link>
        </p>
      )}
    </div>
  );
}

function NewAccountGuideDialog({
  open,
  onOpenChange,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: () => void;
}) {
  const steps = [
    {
      icon: Plus,
      title: "1. 绑定账号",
      desc: "先新增 Telegram 账号，系统会为它启动一个独立 worker。",
    },
    {
      icon: Package,
      title: "2. 复用模板",
      desc: "去插件中心把已有账号的命令、消息、AI 模板分配给新账号。",
    },
    {
      icon: Bot,
      title: "3. 开启插件",
      desc: "按账号开启自动回复、转发、定时任务等能力，再少量测试。",
    },
    {
      icon: CheckCircle2,
      title: "4. 看日志确认",
      desc: "最后看日志和最近调用，确认命令和 AI 调用真的跑通。",
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl overflow-hidden">
        <DialogHeader>
          <DialogTitle>新账号怎么开始？</DialogTitle>
          <DialogDescription>
            按这 4 步走：先把账号接进来，再复用已有模板，最后小范围验证。
          </DialogDescription>
        </DialogHeader>

        <div className="relative rounded-2xl border bg-gradient-to-br from-sky-50 via-background to-emerald-50 p-4 dark:from-sky-950/30 dark:via-background dark:to-emerald-950/20">
          <div className="absolute left-8 right-8 top-10 hidden h-0.5 bg-gradient-to-r from-sky-300 via-emerald-300 to-amber-300 md:block" />
          <div className="grid gap-3 md:grid-cols-4">
            {steps.map((step, idx) => (
              <div
                key={step.title}
                className="relative rounded-xl border bg-card/90 p-3 shadow-sm animate-page-enter"
                style={{ animationDelay: `${idx * 90}ms` }}
              >
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm">
                  <step.icon className="h-5 w-5" />
                </div>
                <div className="text-sm font-semibold">{step.title}</div>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            先看看
          </Button>
          <Button onClick={onCreate}>
            去新增账号 <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
