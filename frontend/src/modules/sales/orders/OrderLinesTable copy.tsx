// import { useMemo } from "react";
// import { Plus, Trash2 } from "lucide-react";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import {
//   Table,
//   TableBody,
//   TableCell,
//   TableFooter,
//   TableHead,
//   TableHeader,
//   TableRow,
// } from "@/components/ui/table";
// import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
// import { listGoodsSalesGoodsGet } from "@/api/generated/sales-goods/sales-goods";
// import type { OrderLineFormData } from "./schemas";

// interface OrderLinesTableProps {
//   lines: OrderLineFormData[];
//   onChange: (lines: OrderLineFormData[]) => void;
//   readOnly: boolean;
// }

// /** Таблица строк спецификации заказа (черновик, Правило №46). */
// export const OrderLinesTable = ({ lines, onChange, readOnly }: OrderLinesTableProps) => {
//   const addLine = () => {
//     onChange([
//       ...lines,
//       {
//         line_no: lines.length + 1,
//         goods_id: "",
//         quantity: 1,
//         price_with_vat: 0,
//         discount_percent: 0,
//         vat_rate_percent: 20,
//         markedForDeletion: false,
//       },
//     ]);
//   };

//   const removeLine = (index: number) => {
//     onChange(lines.filter((_, i) => i !== index));
//   };

//   const updateLine = (index: number, patch: Partial<OrderLineFormData>) => {
//     onChange(lines.map((line, i) => (i === index ? { ...line, ...patch } : line)));
//   };

//   const totals = useMemo(() => {
//     let totalGross = 0;
//     let totalDiscount = 0;
//     let totalNet = 0;
//     let totalVat = 0;
//     for (const line of lines) {
//       const lineTotal = line.quantity * line.price_with_vat;
//       const amountWithDisc = lineTotal * (1 - (line.discount_percent ?? 0) / 100);
//       const vatAmount =
//         line.vat_rate_percent === 0
//           ? 0
//           : (amountWithDisc * line.vat_rate_percent) / (100 + line.vat_rate_percent);
//       totalGross += lineTotal;
//       totalDiscount += lineTotal - amountWithDisc;
//       totalNet += amountWithDisc;
//       totalVat += vatAmount;
//     }
//     return { positionCount: lines.length, totalGross, totalDiscount, totalNet, totalVat };
//   }, [lines]);

//   return (
//     <div className="space-y-2">
//       {!readOnly && (
//         <div className="flex justify-end">
//           <Button variant="outline" size="sm" onClick={addLine} type="button">
//             <Plus className="h-4 w-4 mr-1" /> Добавить строку
//           </Button>
//         </div>
//       )}
//       <div className="rounded-md border overflow-auto max-h-[400px]">
//         <Table className="table-fixed w-full">
//           <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
//             <TableRow className="h-10 hover:bg-transparent">
//               <TableHead style={{ width: 48 }}>№</TableHead>
//               <TableHead style={{ width: 200 }}>Товар *</TableHead>
//               <TableHead style={{ width: 100 }}>Кол-во *</TableHead>
//               <TableHead style={{ width: 120 }}>Цена с НДС *</TableHead>
//               <TableHead style={{ width: 120 }}>Сумма</TableHead>
//               <TableHead style={{ width: 90 }}>Скидка %</TableHead>
//               <TableHead style={{ width: 120 }}>Со скидкой</TableHead>
//               <TableHead style={{ width: 80 }}>НДС % *</TableHead>
//               <TableHead style={{ width: 100 }}>НДС</TableHead>
//               {!readOnly && <TableHead style={{ width: 60 }} />}
//             </TableRow>
//           </TableHeader>
//           <TableBody>
//             {lines.length === 0 ? (
//               <TableRow>
//                 <TableCell colSpan={readOnly ? 9 : 10} className="text-center py-8 text-muted-foreground">
//                   Строки спецификации не добавлены
//                 </TableCell>
//               </TableRow>
//             ) : (
//               lines.map((line, index) => {
//                 const lineTotal = line.quantity * line.price_with_vat;
//                 const amountWithDisc = lineTotal * (1 - (line.discount_percent ?? 0) / 100);
//                 const vatAmount =
//                   line.vat_rate_percent === 0
//                     ? 0
//                     : (amountWithDisc * line.vat_rate_percent) / (100 + line.vat_rate_percent);
//                 return (
//                   <TableRow key={line.id ?? `new-${index}`}>
//                     <TableCell className="py-1 align-top">{index + 1}</TableCell>
//                     <TableCell className="py-1 align-top">
//                       <ReferenceSelect
//                         fetchFn={async (params) => {
//                           const response = await listGoodsSalesGoodsGet({
//                             skip: params.skip,
//                             limit: params.limit,
//                             search: params.search,
//                           });
//                           const items = (response?.data?.items ?? []).map((item) => ({
//                             id: item.id,
//                             name: item.name,
//                           }));
//                           return { items, total: response?.data?.total ?? 0 };
//                         }}
//                         queryKey={["goods"]}
//                         value={line.goods_id}
//                         onValueChange={(v) => updateLine(index, { goods_id: v })}
//                         placeholder="Выберите товар..."
//                         heading="Товары"
//                         limit={50}
//                         disabled={readOnly}
//                       />
//                     </TableCell>
//                     <TableCell className="py-1 align-top">
//                       <Input
//                         type="number"
//                         min={0}
//                         step="any"
//                         value={line.quantity}
//                         onChange={(e) => updateLine(index, { quantity: Number(e.target.value) || 0 })}
//                         disabled={readOnly}
//                         className="h-8"
//                       />
//                     </TableCell>
//                     <TableCell className="py-1 align-top">
//                       <Input
//                         type="number"
//                         min={0}
//                         step="0.01"
//                         value={line.price_with_vat}
//                         onChange={(e) => updateLine(index, { price_with_vat: Number(e.target.value) || 0 })}
//                         disabled={readOnly}
//                         className="h-8"
//                       />
//                     </TableCell>
//                     <TableCell className="py-1 align-top text-right">{lineTotal.toFixed(2)}</TableCell>
//                     <TableCell className="py-1 align-top">
//                       <Input
//                         type="number"
//                         min={0}
//                         max={100}
//                         step="0.01"
//                         value={line.discount_percent ?? 0}
//                         onChange={(e) => updateLine(index, { discount_percent: Number(e.target.value) || 0 })}
//                         disabled={readOnly}
//                         className="h-8"
//                       />
//                     </TableCell>
//                     <TableCell className="py-1 align-top text-right">{amountWithDisc.toFixed(2)}</TableCell>
//                     <TableCell className="py-1 align-top">
//                       <Input
//                         type="number"
//                         min={0}
//                         max={100}
//                         step="0.01"
//                         value={line.vat_rate_percent}
//                         onChange={(e) => updateLine(index, { vat_rate_percent: Number(e.target.value) || 0 })}
//                         disabled={readOnly}
//                         className="h-8"
//                       />
//                     </TableCell>
//                     <TableCell className="py-1 align-top text-right">{vatAmount.toFixed(2)}</TableCell>
//                     {!readOnly && (
//                       <TableCell className="py-1 align-top">
//                         <Button
//                           variant="ghost"
//                           size="icon"
//                           className="h-7 w-7 text-destructive hover:text-destructive"
//                           onClick={() => removeLine(index)}
//                           type="button"
//                         >
//                           <Trash2 className="h-4 w-4" />
//                         </Button>
//                       </TableCell>
//                     )}
//                   </TableRow>
//                 );
//               })
//             )}
//           </TableBody>
//           <TableFooter>
//             <TableRow>
//               <TableCell colSpan={3} className="text-right font-medium">Итого:</TableCell>
//               <TableCell className="text-right">{totals.positionCount} поз.</TableCell>
//               <TableCell className="text-right">{totals.totalGross.toFixed(2)}</TableCell>
//               <TableCell className="text-right">{totals.totalDiscount.toFixed(2)}</TableCell>
//               <TableCell className="text-right">{totals.totalNet.toFixed(2)}</TableCell>
//               <TableCell className="text-right">{totals.totalVat.toFixed(2)}</TableCell>
//               {!readOnly && <TableCell />}
//             </TableRow>
//           </TableFooter>
//         </Table>
//       </div>
//     </div>
//   );
// };