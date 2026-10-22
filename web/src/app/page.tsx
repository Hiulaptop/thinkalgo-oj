import { Cpu, Radio, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { VerdictBadge } from "@/components/ui/verdict-badge";

const FEATURES = [
  { icon: Cpu, title: "Hàng trăm đề bài", text: "Từ khởi động đến thử thách, lọc theo chủ đề và độ khó." },
  { icon: Radio, title: "Chấm bài trực tiếp", text: "Nộp xong là thấy kết quả từng test ngay lập tức." },
  { icon: Trophy, title: "Cuộc thi & xếp hạng", text: "Thi đấu cùng bạn bè, leo bảng điểm mỗi tuần." },
];

export default function HomePage() {
  return (
    <>
      <section className="flex flex-col items-start gap-6 py-10 sm:py-16">
        <div className="flex flex-wrap gap-2" aria-label="Ví dụ trạng thái chấm bài">
          <VerdictBadge status="AC" />
          <VerdictBadge status="WA" />
          <VerdictBadge status="TLE" />
        </div>
        <h1 className="max-w-3xl text-heading sm:text-display">Luyện thuật toán, vui như chơi!</h1>
        <p className="max-w-2xl text-body-lg">
          ThinkAlgo OJ là nơi bạn giải đề, nộp bài và nhận kết quả ngay. Bắt đầu từ bài dễ nhất, rồi cùng leo bảng
          xếp hạng.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <a href="/problems/">Xem đề bài</a>
          </Button>
          <Button asChild variant="secondary">
            <a href="/contests/">Tham gia cuộc thi</a>
          </Button>
        </div>
      </section>

      <section aria-labelledby="features" className="grid gap-6 pb-8 md:grid-cols-3">
        <h2 id="features" className="sr-only">
          Điểm nổi bật
        </h2>
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <Card key={title} interactive tabIndex={0}>
            <span className="mb-4 grid size-12 place-items-center rounded-2xl border-[3px] border-edge bg-amber text-cocoa interactive motion-safe:group-hover/card:rotate-6 motion-safe:group-hover/card:scale-110">
              <Icon aria-hidden="true" className="size-6" />
            </span>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{text}</CardDescription>
          </Card>
        ))}
      </section>
    </>
  );
}
