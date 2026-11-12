// import {
//   FormTabs,
//   FormTabPanel,
//   FormSection,
//   ReadOnlyField,
//   ReadOnlyGroup,
// } from "@/lib/form-blocks";
// import { FileText } from "lucide-react";

// <FormTabs defaultValue="main">
//   <FormTabPanel value="main" label="Документ">
//     <FormSection
//       title="Реквизиты"
//       description="Основные поля документа"
//       icon={FileText}
//       columns={2}
//     >
//       {/* редактируемые поля через Controller */}
//     </FormSection>

//     <ReadOnlyGroup
//       title="Служебная информация"
//       description="Заполняется автоматически и не редактируется"
//       columns={2}
//     >
//       <ReadOnlyField label="Автор" value={entity.author_name} />
//       <ReadOnlyField label="Раздел" value={entity.section_name} />
//       <ReadOnlyField
//         label="Создан"
//         value={entity.created_at}
//         hint="Дата и время создания записи"
//       />
//       <ReadOnlyField
//         label="Версия"
//         value={entity.version}
//         hint="Увеличивается при каждом сохранении"
//       />
//     </ReadOnlyGroup>
//   </FormTabPanel>
// </FormTabs>