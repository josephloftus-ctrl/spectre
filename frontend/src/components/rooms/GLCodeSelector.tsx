import { useEffect, useState } from 'react';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { fetchGLCodes } from '@/lib/api';

interface GLCodeSelectorProps {
    siteId: string;
    value: string | null;
    onChange: (glCode: string) => void;
    placeholder?: string;
    disabled?: boolean;
    className?: string;
    allowCustom?: boolean;
}

export function GLCodeSelector({
    siteId,
    value,
    onChange,
    placeholder = 'Select GL code...',
    disabled = false,
    className,
    allowCustom = true,
}: GLCodeSelectorProps) {
    const [glCodes, setGLCodes] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [showCustomInput, setShowCustomInput] = useState(false);
    const [customValue, setCustomValue] = useState('');

    useEffect(() => {
        if (!siteId) {
            setGLCodes([]);
            return;
        }

        const loadGLCodes = async () => {
            setLoading(true);
            try {
                const { gl_codes } = await fetchGLCodes(siteId);
                setGLCodes(gl_codes);
            } catch (error) {
                console.error('Failed to load GL codes:', error);
                setGLCodes([]);
            } finally {
                setLoading(false);
            }
        };

        loadGLCodes();
    }, [siteId]);

    // Check if current value is a custom one
    const isCustomValue = value && !glCodes.includes(value) && value !== '__custom__';

    if (showCustomInput || isCustomValue) {
        return (
            <div className="flex gap-2">
                <Input
                    value={isCustomValue ? value : customValue}
                    onChange={(e) => {
                        setCustomValue(e.target.value);
                        onChange(e.target.value);
                    }}
                    placeholder="Enter GL code..."
                    className={className}
                    disabled={disabled}
                />
                <button
                    type="button"
                    onClick={() => {
                        setShowCustomInput(false);
                        setCustomValue('');
                        onChange('');
                    }}
                    className="px-2 text-xs text-muted-foreground hover:text-foreground"
                >
                    Cancel
                </button>
            </div>
        );
    }

    return (
        <Select
            value={value || undefined}
            onValueChange={(v) => {
                if (v === '__custom__') {
                    setShowCustomInput(true);
                } else {
                    onChange(v);
                }
            }}
            disabled={disabled || loading || !siteId}
        >
            <SelectTrigger className={className}>
                <SelectValue placeholder={loading ? 'Loading...' : placeholder} />
            </SelectTrigger>
            <SelectContent>
                {glCodes.length === 0 && !loading && (
                    <SelectItem value="__none__" disabled>
                        No GL codes found
                    </SelectItem>
                )}
                {glCodes.map(code => (
                    <SelectItem key={code} value={code}>
                        {code}
                    </SelectItem>
                ))}
                {allowCustom && glCodes.length > 0 && (
                    <SelectItem value="__custom__">
                        <span className="text-muted-foreground">+ Enter custom...</span>
                    </SelectItem>
                )}
            </SelectContent>
        </Select>
    );
}
