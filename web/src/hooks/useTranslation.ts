/**
 * 翻译 Hook
 *
 * 提供便捷的翻译函数
 */
import { useLocale } from "@/contexts/LocaleContext";
import { translations, type TranslationKey } from "@/locales";

/**
 * 使用翻译的 Hook
 */
export function useTranslation(category: TranslationKey) {
  const { locale } = useLocale();

  /**
   * 获取翻译文本
   * @param key 翻译键
   * @returns 翻译后的文本
   */
  const t = (key: string): string => {
    const categoryTranslations = translations[category] as Record<
      string,
      Record<string, string>
    >;
    return categoryTranslations[key]?.[locale] || key;
  };

  return { t };
}
