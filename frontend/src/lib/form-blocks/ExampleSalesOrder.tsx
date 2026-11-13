// import { FormTabs, FormTabPanel, FieldsGrid, FieldBlock, TableSection } from "@/lib/form-blocks";
// import { Controller } from "react-hook-form";
// import { Input } from "@/components/ui/input";
// import { Button } from "@/components/ui/button";
// import { Plus } from "lucide-react";

// // Внутри компонента вкладки «Основное»
// <FieldsGrid cols={2}>
//   <FieldBlock label="Клиент" required htmlFor="client_id" error={errors.client_id?.message}>
//     <Controller
//       name="client_id"
//       control={control}
//       render={({ field }) => (
//         <ReferenceSelect
//           fetchFn={fetchClients}
//           queryKey={["clients"]}
//           value={field.value}
//           onValueChange={field.onChange}
//           placeholder="Выберите клиента..."
//           selectedLabel={initialData?.client_name ?? "Выберите клиента..."}
//         />
//       )}
//     />
//   </FieldBlock>

//   <FieldBlock label="Регион" htmlFor="region_id">
//     <Controller name="region_id" control={control} render={({ field }) => (/* ... */)} />
//   </FieldBlock>
// </FieldsGrid>

// <TableSection
//   title="Строки заказа"
//   actions={
//     <Button variant="outline" size="sm" onClick={addLine}>
//       <Plus className="h-4 w-4 mr-1" /> Добавить строку
//     </Button>
//   }
//   isLoading={isLinesLoading}
// >
//   <OrderLinesTable lines={linesDraft} onChange={setLinesDraft} />
// </TableSection>

// // Вкладки в модалке
// <FormTabs value={activeTab} onValueChange={setActiveTab}>
//   <FormTabPanel value="main" label="Основное" dirty={hasMainChanges}>
//     <SalesOrderMainTab control={control} errors={errors} />
//   </FormTabPanel>
//   <FormTabPanel value="payments" label="Оплаты" dirty={hasPaymentsChanges} counter={3}>
//     <SalesOrderPaymentsTab control={control} errors={errors} />
//   </FormTabPanel>
// </FormTabs>