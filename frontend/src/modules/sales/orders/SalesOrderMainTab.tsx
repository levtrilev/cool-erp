import { Controller, type Control, type FieldErrors } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { listCompaniesBusinessPartnersCompaniesGet } from "@/api/generated/business-partners-companies/business-partners-companies";
import { readUsersUsersGet } from "@/api/generated/users/users";
import { getCurrenciesCurrenciesGet } from "@/api/generated/currencies/currencies";
import { FieldsGrid } from "@/lib/form-blocks/FieldsGrid";
import { FieldBlock } from "@/lib/form-blocks/FieldBlock";
import { TableSection } from "@/lib/form-blocks/TableSection";
import { OrderLinesTable } from "./OrderLinesTable";
import type { SalesOrderFormData, OrderLineFormData } from "./schemas";
import type { SalesOrderResponseSchema } from "@/api/generated/coolERP.schemas";

interface SalesOrderMainTabProps {
  control: Control<SalesOrderFormData>;
  errors: FieldErrors<SalesOrderFormData>;
  readOnly: boolean;
  initialData: SalesOrderResponseSchema | null;
  orderLinesDraft: OrderLineFormData[];
  setOrderLinesDraft: (lines: OrderLineFormData[]) => void;
  totalAmount: number;
}

/** Вкладка «Заказ»: основные данные + спецификация. */
export const SalesOrderMainTab = ({
  control,
  errors,
  readOnly,
  initialData,
  orderLinesDraft,
  setOrderLinesDraft,
  totalAmount,
}: SalesOrderMainTabProps) => {
  return (
    <div className="space-y-6">
      <FieldsGrid cols={2}>
        <FieldBlock label="Поставщик" required htmlFor="supplier_id" error={errors.supplier_id?.message as string | undefined}>
          <Controller
            name="supplier_id"
            control={control}
            render={({ field }) => (
              <ReferenceSelect
                fetchFn={async (params) => {
                  const response = await listCompaniesBusinessPartnersCompaniesGet({
                    skip: params.skip,
                    limit: params.limit,
                    search: params.search,
                  });
                  const items = (response?.data?.items ?? []).map((item) => ({
                    id: item.id,
                    name: item.name,
                  }));
                  return { items, total: response?.data?.total ?? 0 };
                }}
                queryKey={["companies"]}
                value={field.value}
                onValueChange={field.onChange}
                placeholder="Выберите поставщика..."
                selectedLabel={(initialData as (SalesOrderResponseSchema & { supplier_name?: string }) | null)?.supplier_name ?? "Выберите поставщика..."}
                heading="Компании"
                limit={50}
                disabled={readOnly}
              />
            )}
          />
        </FieldBlock>

        <FieldBlock label="Заказчик" required htmlFor="customer_id" error={errors.customer_id?.message as string | undefined}>
          <Controller
            name="customer_id"
            control={control}
            render={({ field }) => (
              <ReferenceSelect
                fetchFn={async (params) => {
                  const response = await listCompaniesBusinessPartnersCompaniesGet({
                    skip: params.skip,
                    limit: params.limit,
                    search: params.search,
                  });
                  const items = (response?.data?.items ?? []).map((item) => ({
                    id: item.id,
                    name: item.name,
                  }));
                  return { items, total: response?.data?.total ?? 0 };
                }}
                queryKey={["companies"]}
                value={field.value}
                onValueChange={field.onChange}
                placeholder="Выберите заказчика..."
                selectedLabel={(initialData as (SalesOrderResponseSchema & { customer_name?: string }) | null)?.customer_name ?? "Выберите заказчика..."}
                heading="Компании"
                limit={50}
                disabled={readOnly}
              />
            )}
          />
        </FieldBlock>

        <FieldBlock label="Контактное лицо" required htmlFor="contact" error={errors.contact?.message as string | undefined}>
          <Controller
            name="contact"
            control={control}
            render={({ field }) => (
              <Input id="contact" {...field} placeholder="Имя или телефон контакта" disabled={readOnly} />
            )}
          />
        </FieldBlock>

        <FieldBlock label="Менеджер" required htmlFor="manager_id" error={errors.manager_id?.message as string | undefined}>
          <Controller
            name="manager_id"
            control={control}
            render={({ field }) => (
              <ReferenceSelect
                fetchFn={async (params) => {
                  const response = await readUsersUsersGet({
                    skip: params.skip,
                    limit: params.limit,
                    search: params.search,
                  });
                  const items = (response?.data?.items ?? []).map((item) => ({
                    id: item.id,
                    name: item.name,
                  }));
                  return { items, total: response?.data?.total ?? 0 };
                }}
                queryKey={["users"]}
                value={field.value}
                onValueChange={field.onChange}
                placeholder="Выберите менеджера..."
                selectedLabel={(initialData as (SalesOrderResponseSchema & { manager_name?: string }) | null)?.manager_name ?? "Выберите менеджера..."}
                heading="Сотрудники"
                limit={100}
                disabled={readOnly}
              />
            )}
          />
        </FieldBlock>

        <FieldBlock label="Дата исполнения заказа" required htmlFor="delivery_due_date" error={errors.delivery_due_date?.message as string | undefined}>
          <Controller
            name="delivery_due_date"
            control={control}
            render={({ field }) => (
              <Input id="delivery_due_date" type="date" {...field} value={field.value ?? ""} disabled={readOnly} />
            )}
          />
        </FieldBlock>

        <FieldBlock label="Валюта заказа" required htmlFor="currency_id" error={errors.currency_id?.message as string | undefined}>
          <Controller
            name="currency_id"
            control={control}
            render={({ field }) => (
              <ReferenceSelect
                fetchFn={async (params) => {
                  const response = await getCurrenciesCurrenciesGet({
                    skip: params.skip,
                    limit: params.limit,
                    search: params.search,
                  });
                  const items = (response?.data?.items ?? []).map((item) => ({
                    id: item.id,
                    name: item.name,
                  }));
                  return { items, total: response?.data?.total ?? 0 };
                }}
                queryKey={["currencies"]}
                value={field.value}
                onValueChange={field.onChange}
                placeholder="Выберите валюту..."
                selectedLabel={(initialData as (SalesOrderResponseSchema & { currency_name?: string }) | null)?.currency_name ?? "Выберите валюту..."}
                heading="Валюты"
                limit={100}
                disabled={readOnly}
              />
            )}
          />
        </FieldBlock>

        <FieldBlock label="Схема оплаты" htmlFor="payment_scheme">
          <Controller
            name="payment_scheme"
            control={control}
            render={({ field }) => (
              <Input
                id="payment_scheme"
                {...field}
                value={field.value ?? ""}
                placeholder="Например: 20% предоплата, 80% по факту отгрузки"
                disabled={readOnly}
              />
            )}
          />
        </FieldBlock>

        <FieldBlock label="Сумма заказа" htmlFor="total_amount">
          <div className="flex h-9 w-full items-center rounded-md border border-input bg-muted px-3 text-sm text-muted-foreground">
            {totalAmount.toFixed(2)}
          </div>
        </FieldBlock>
      </FieldsGrid>

      <TableSection title="Спецификация заказа" description="Строки заказа с товарами и ценами">
        <OrderLinesTable lines={orderLinesDraft} onChange={setOrderLinesDraft} readOnly={readOnly} />
      </TableSection>
    </div>
  );
};