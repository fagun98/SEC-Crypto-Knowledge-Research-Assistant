import AppShell from "@/components/AppShell";
import ReportViewer from "@/components/ReportViewer";
import WeeklyReportOverview from "@/components/WeeklyReportOverview";

export default function ReportsPage() {
  return (
    <AppShell>
      <WeeklyReportOverview />
      <div id="latest-report" className="scroll-mt-24 px-6 py-14 sm:px-8 lg:px-12 lg:py-20">
        <div className="mx-auto max-w-[92rem]">
          <div className="mb-9 flex flex-col justify-between gap-5 border-b border-line/70 pb-7 sm:flex-row sm:items-end">
            <div>
              <div className="eyebrow">Intelligence archive</div>
              <h2 className="mt-3 font-serif text-3xl text-white sm:text-4xl">Latest weekly memorandum</h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-slate-500 sm:text-right">
              Select an issue from the archive to compare regulatory signals, enforcement themes, and
              action priorities week over week.
            </p>
          </div>
          <ReportViewer />
        </div>
      </div>
    </AppShell>
  );
}
