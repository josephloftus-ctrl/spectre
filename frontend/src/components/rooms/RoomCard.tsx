import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { cn } from '@/lib/utils';
import { RoomWithItems } from '@/lib/api';
import { RoomItem } from './RoomItem';
import { Package } from 'lucide-react';

interface RoomCardProps {
    room: RoomWithItems;
    isOver?: boolean;
}

export function RoomCard({ room, isOver }: RoomCardProps) {
    const { setNodeRef, isOver: isOverDroppable } = useDroppable({
        id: room.name,
        data: {
            type: 'room',
            room,
        },
    });

    const itemIds = room.items.map(item => item.sku);
    const showDropIndicator = isOver || isOverDroppable;

    return (
        <div
            ref={setNodeRef}
            className={cn(
                'flex flex-col rounded-lg border bg-card',
                'min-h-[200px] max-h-[500px]',
                showDropIndicator && 'ring-2 ring-primary ring-offset-2',
            )}
        >
            {/* Header */}
            <div
                className="flex items-center gap-2 p-3 border-b"
                style={{
                    borderLeftWidth: '4px',
                    borderLeftColor: room.color || '#94A3B8',
                }}
            >
                <div className="flex-1">
                    <h3 className="font-medium">{room.display_name}</h3>
                    <p className="text-xs text-muted-foreground">
                        {room.item_count} {room.item_count === 1 ? 'item' : 'items'}
                    </p>
                </div>
                {room.is_predefined && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-muted text-muted-foreground rounded">
                        System
                    </span>
                )}
            </div>

            {/* Items */}
            <div className="flex-1 p-2 overflow-y-auto">
                <SortableContext
                    items={itemIds}
                    strategy={verticalListSortingStrategy}
                >
                    {room.items.length === 0 ? (
                        <div className={cn(
                            'flex flex-col items-center justify-center h-full min-h-[100px]',
                            'text-muted-foreground text-sm',
                            showDropIndicator && 'bg-primary/5 rounded-md',
                        )}>
                            <Package className="h-8 w-8 mb-2 opacity-50" />
                            <p>Drop items here</p>
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {room.items.map(item => (
                                <RoomItem key={item.sku} item={item} />
                            ))}
                        </div>
                    )}
                </SortableContext>
            </div>
        </div>
    );
}
