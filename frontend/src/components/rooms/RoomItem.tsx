import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Package } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ItemLocation } from '@/lib/api';

interface RoomItemProps {
    item: ItemLocation;
    isDragOverlay?: boolean;
}

export function RoomItem({ item, isDragOverlay = false }: RoomItemProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({
        id: item.sku,
        data: {
            type: 'item',
            item,
        },
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                'flex items-center gap-2 p-2 bg-card border rounded-md',
                'hover:border-primary/50 transition-colors',
                isDragging && 'opacity-50',
                isDragOverlay && 'shadow-lg border-primary',
            )}
        >
            <button
                {...attributes}
                {...listeners}
                className="cursor-grab touch-none p-1 hover:bg-accent rounded"
                aria-label="Drag handle"
            >
                <GripVertical className="h-4 w-4 text-muted-foreground" />
            </button>
            <Package className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{item.sku}</p>
            </div>
            {item.auto_assigned && (
                <span className="text-[10px] px-1.5 py-0.5 bg-muted text-muted-foreground rounded">
                    Auto
                </span>
            )}
        </div>
    );
}

// Static version for drag overlay
export function RoomItemOverlay({ item }: { item: ItemLocation }) {
    return (
        <div className="flex items-center gap-2 p-2 bg-card border border-primary rounded-md shadow-lg">
            <GripVertical className="h-4 w-4 text-muted-foreground" />
            <Package className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{item.sku}</p>
            </div>
        </div>
    );
}
