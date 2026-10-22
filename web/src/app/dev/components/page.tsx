import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VerdictBadge } from "@/components/ui/verdict-badge";

export const metadata: Metadata = { title: "Thư viện component", robots: { index: false } };

const SWATCHES = [
  { name: "Cream", cls: "bg-cream text-cocoa", hex: "#FFF1D1" },
  { name: "Sand", cls: "bg-sand text-cocoa", hex: "#F9E6A8" },
  { name: "Amber", cls: "bg-amber text-cocoa", hex: "#F2A900" },
  { name: "Orange", cls: "bg-orange text-cocoa", hex: "#FF9100" },
  { name: "Copper", cls: "bg-copper text-white", hex: "#CC6F00" },
  { name: "Cocoa", cls: "bg-cocoa text-cream", hex: "#4D2A00" },
  { name: "Red", cls: "bg-red text-white", hex: "#DF301C" },
  { name: "Leaf", cls: "bg-leaf text-cocoa", hex: "#6CC24A" },
  { name: "Cyan", cls: "bg-cyan text-cocoa", hex: "#00B7CD" },
  { name: "Espresso", cls: "bg-espresso text-cream", hex: "#331B00" },
];

const VERDICTS = ["AC", "WA", "TLE", "MLE", "OLE", "RE", "IR", "CE", "PARTIAL", "PENDING", "XYZ"];

const SUBMISSIONS = [
  { id: "#10231", problem: "Tổng hai số", verdict: "AC", time: "0.02s", mem: "3.1 MB" },
  { id: "#10230", problem: "Dãy con tăng dài nhất", verdict: "TLE", time: "2.00s", mem: "14.8 MB" },
  { id: "#10229", problem: "Đường đi ngắn nhất", verdict: "WA", time: "0.11s", mem: "9.4 MB" },
  { id: "#10228", problem: "Xâu đối xứng", verdict: "PENDING", time: "-", mem: "-" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="mb-4 text-heading-sm">{title}</h2>
      {children}
    </section>
  );
}

export default function ComponentGalleryPage() {
  if (process.env.NODE_ENV === "production") notFound();

  return (
    <>
      <h1 className="mb-2 text-heading">Thư viện component</h1>
      <p className="mb-10 text-body-lg">
        Trang nội bộ để xem component ở mọi trạng thái. Rê chuột, bấm Tab để xem hover và focus. Chỉ có ở môi trường
        phát triển.
      </p>

      <Section title="Màu">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {SWATCHES.map((s) => (
            <div key={s.name} className={`rounded-card border-[3px] border-edge p-4 shadow-hard-sm ${s.cls}`}>
              <p className="font-extrabold">{s.name}</p>
              <p className="font-mono text-caption">{s.hex}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Chữ">
        <p className="font-heading text-display font-extrabold">Display 56</p>
        <p className="font-heading text-heading font-extrabold">Tiêu đề 40: Thuật toán Việt Nam</p>
        <p className="font-heading text-subheading font-bold">Tiêu đề phụ 24: Đường đi ngắn nhất</p>
        <p className="text-body-lg">Nội dung 18: Cho dãy số nguyên, tìm đoạn con có tổng lớn nhất. Ăn quả nhớ kẻ trồng cây.</p>
        <p className="text-body">Nội dung 16: Giới hạn thời gian 1 giây, bộ nhớ 256 MB. Ươ, ơ, ê, ô, â, ă, đ.</p>
        <p className="font-mono text-caption">{"for (int i = 0; i < n; ++i) // lặp qua từng phần tử"}</p>
      </Section>

      <Section title="Button">
        <div className="flex flex-wrap items-center gap-4">
          <Button>Nộp bài</Button>
          <Button variant="secondary">Xem đề</Button>
          <Button variant="ghost">Bỏ qua</Button>
          <Button variant="danger">Xoá bài nộp</Button>
          <Button disabled>Vô hiệu</Button>
          <Button size="sm">Nhỏ</Button>
        </div>
      </Section>

      <Section title="Badge và VerdictBadge">
        <div className="mb-4 flex flex-wrap gap-2">
          <Badge>Mặc định</Badge>
          <Badge variant="amber">Amber</Badge>
          <Badge variant="orange">Orange</Badge>
          <Badge variant="leaf">Leaf</Badge>
          <Badge variant="cyan">Cyan</Badge>
          <Badge variant="red">Red</Badge>
          <Badge variant="dark">Cocoa</Badge>
        </div>
        <div className="flex flex-wrap gap-3">
          {VERDICTS.map((v) => (
            <VerdictBadge key={v} status={v} />
          ))}
        </div>
      </Section>

      <Section title="Card">
        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardTitle>Card tĩnh</CardTitle>
            <CardDescription>Không bấm được nên không có hover.</CardDescription>
          </Card>
          <Card interactive tabIndex={0}>
            <CardTitle>Card bấm được</CardTitle>
            <CardDescription>Rê chuột: nâng lên, nghiêng nhẹ, bóng to hơn.</CardDescription>
          </Card>
          <Card tone="muted">
            <CardTitle>Card nền phụ</CardTitle>
            <CardDescription>Dùng cho khối phụ, thống kê.</CardDescription>
          </Card>
        </div>
      </Section>

      <Section title="Input">
        <div className="grid max-w-xl gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="g-username">Tên đăng nhập</Label>
            <Input id="g-username" placeholder="vd: nguyenvana" />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="g-error">Có lỗi</Label>
            <Input id="g-error" aria-invalid="true" aria-describedby="g-error-msg" defaultValue="abc" />
            <p id="g-error-msg" className="text-caption font-bold">
              ⚠ Tên đăng nhập phải có ít nhất 4 ký tự.
            </p>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="g-disabled">Vô hiệu</Label>
            <Input id="g-disabled" disabled defaultValue="Không chỉnh sửa được" />
          </div>
        </div>
      </Section>

      <Section title="Table">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mã</TableHead>
              <TableHead>Đề bài</TableHead>
              <TableHead>Kết quả</TableHead>
              <TableHead>Thời gian</TableHead>
              <TableHead>Bộ nhớ</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {SUBMISSIONS.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="font-mono">{row.id}</TableCell>
                <TableCell className="font-bold">
                  <span className="inline-block transition-transform duration-150 motion-safe:group-hover/row:translate-x-1">
                    {row.problem}
                  </span>
                </TableCell>
                <TableCell>
                  <VerdictBadge status={row.verdict} />
                </TableCell>
                <TableCell className="font-mono">{row.time}</TableCell>
                <TableCell className="font-mono">{row.mem}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Section>

      <Section title="Tabs">
        <Tabs defaultValue="statement">
          <TabsList>
            <TabsTrigger value="statement">Đề bài</TabsTrigger>
            <TabsTrigger value="submissions">Bài nộp</TabsTrigger>
            <TabsTrigger value="stats">Thống kê</TabsTrigger>
          </TabsList>
          <TabsContent value="statement">
            <Card tone="muted">Nội dung đề bài hiển thị ở đây.</Card>
          </TabsContent>
          <TabsContent value="submissions">
            <Card tone="muted">Danh sách bài nộp của bạn.</Card>
          </TabsContent>
          <TabsContent value="stats">
            <Card tone="muted">Thống kê tỉ lệ AC theo ngôn ngữ.</Card>
          </TabsContent>
        </Tabs>
      </Section>
    </>
  );
}
