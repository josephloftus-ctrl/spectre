import { useEffect, useState } from 'react';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    SelectSeparator,
} from '@/components/ui/select';
import { fetchRooms, RoomInfo } from '@/lib/api';

interface RoomSelectorProps {
    siteId: string;
    value: string | null;
    onChange: (room: string) => void;
    includeUnassigned?: boolean;
    placeholder?: string;
    disabled?: boolean;
    className?: string;
}

export function RoomSelector({
    siteId,
    value,
    onChange,
    includeUnassigned = true,
    placeholder = 'Select room...',
    disabled = false,
    className,
}: RoomSelectorProps) {
    const [rooms, setRooms] = useState<RoomInfo[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!siteId) {
            setRooms([]);
            return;
        }

        const loadRooms = async () => {
            setLoading(true);
            try {
                const { rooms: fetchedRooms } = await fetchRooms(siteId, true);
                // Filter out NEVER INVENTORY unless it's the current value
                let filtered = fetchedRooms.filter(
                    r => r.name !== 'NEVER INVENTORY' || r.name === value
                );
                // Filter out UNASSIGNED if not wanted
                if (!includeUnassigned) {
                    filtered = filtered.filter(r => r.name !== 'UNASSIGNED');
                }
                setRooms(filtered);
            } catch (error) {
                console.error('Failed to load rooms:', error);
                setRooms([]);
            } finally {
                setLoading(false);
            }
        };

        loadRooms();
    }, [siteId, includeUnassigned, value]);

    // Separate predefined and custom rooms
    const predefinedRooms = rooms.filter(r => r.is_predefined && r.name !== 'UNASSIGNED');
    const customRooms = rooms.filter(r => !r.is_predefined);
    const unassigned = rooms.find(r => r.name === 'UNASSIGNED');

    return (
        <Select
            value={value || undefined}
            onValueChange={onChange}
            disabled={disabled || loading || !siteId}
        >
            <SelectTrigger className={className}>
                <SelectValue placeholder={loading ? 'Loading...' : placeholder} />
            </SelectTrigger>
            <SelectContent>
                {/* Predefined rooms */}
                {predefinedRooms.map(room => (
                    <SelectItem key={room.name} value={room.name}>
                        <div className="flex items-center gap-2">
                            {room.color && (
                                <span
                                    className="w-2 h-2 rounded-full"
                                    style={{ backgroundColor: room.color }}
                                />
                            )}
                            <span>{room.display_name}</span>
                            <span className="text-muted-foreground text-xs">
                                ({room.item_count})
                            </span>
                        </div>
                    </SelectItem>
                ))}

                {/* Custom rooms */}
                {customRooms.length > 0 && (
                    <>
                        <SelectSeparator />
                        {customRooms.map(room => (
                            <SelectItem key={room.name} value={room.name}>
                                <div className="flex items-center gap-2">
                                    {room.color && (
                                        <span
                                            className="w-2 h-2 rounded-full"
                                            style={{ backgroundColor: room.color }}
                                        />
                                    )}
                                    <span>{room.display_name}</span>
                                    <span className="text-muted-foreground text-xs">
                                        ({room.item_count})
                                    </span>
                                </div>
                            </SelectItem>
                        ))}
                    </>
                )}

                {/* Unassigned at the bottom */}
                {unassigned && includeUnassigned && (
                    <>
                        <SelectSeparator />
                        <SelectItem value="UNASSIGNED">
                            <div className="flex items-center gap-2">
                                <span
                                    className="w-2 h-2 rounded-full"
                                    style={{ backgroundColor: unassigned.color || '#9CA3AF' }}
                                />
                                <span className="text-muted-foreground">Unassigned</span>
                                <span className="text-muted-foreground text-xs">
                                    ({unassigned.item_count})
                                </span>
                            </div>
                        </SelectItem>
                    </>
                )}
            </SelectContent>
        </Select>
    );
}
