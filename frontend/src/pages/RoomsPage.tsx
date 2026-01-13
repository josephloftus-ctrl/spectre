import { useState, useCallback, useEffect } from 'react';
import {
    DndContext,
    DragOverlay,
    closestCorners,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragStartEvent,
    DragEndEvent,
    DragOverEvent,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { RefreshCw, LayoutGrid } from 'lucide-react';
import {
    fetchSites,
    fetchItemsByRoom,
    moveItemToRoom,
    RoomWithItems,
    ItemLocation,
} from '@/lib/api';
import { RoomCard, RoomItemOverlay, CreateRoomDialog } from '@/components/rooms';

export function RoomsPage() {
    const queryClient = useQueryClient();
    const [selectedSite, setSelectedSite] = useState<string>('');
    const [activeItem, setActiveItem] = useState<ItemLocation | null>(null);
    const [rooms, setRooms] = useState<RoomWithItems[]>([]);

    // Sensors for drag-and-drop
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Fetch sites
    const { data: sitesData } = useQuery({
        queryKey: ['sites'],
        queryFn: fetchSites,
    });

    // Fetch items by room
    const {
        data: roomsData,
        isLoading,
        refetch,
    } = useQuery({
        queryKey: ['rooms-items', selectedSite],
        queryFn: () => fetchItemsByRoom(selectedSite),
        enabled: !!selectedSite,
    });

    // Sync rooms state with fetched data
    useEffect(() => {
        if (roomsData?.rooms) {
            setRooms(roomsData.rooms);
        }
    }, [roomsData]);

    // Auto-select first site
    useEffect(() => {
        if (!selectedSite && sitesData?.sites?.length) {
            setSelectedSite(sitesData.sites[0].site_id);
        }
    }, [sitesData, selectedSite]);

    // Find item and its room
    const findItemAndRoom = useCallback(
        (sku: string): { item: ItemLocation | null; roomName: string | null } => {
            for (const room of rooms) {
                const item = room.items.find(i => i.sku === sku);
                if (item) {
                    return { item, roomName: room.name };
                }
            }
            return { item: null, roomName: null };
        },
        [rooms]
    );

    // Handle drag start
    const handleDragStart = useCallback(
        (event: DragStartEvent) => {
            const { active } = event;
            const { item } = findItemAndRoom(active.id as string);
            setActiveItem(item);
        },
        [findItemAndRoom]
    );

    // Handle drag over (for preview)
    const handleDragOver = useCallback(
        (event: DragOverEvent) => {
            const { active, over } = event;
            if (!over) return;

            const activeId = active.id as string;
            const overId = over.id as string;

            // Find source and destination rooms
            const { roomName: sourceRoom } = findItemAndRoom(activeId);
            const destinationRoom = over.data?.current?.type === 'room'
                ? overId
                : findItemAndRoom(overId).roomName;

            if (!sourceRoom || !destinationRoom || sourceRoom === destinationRoom) {
                return;
            }

            // Optimistically move the item in local state
            setRooms(prevRooms => {
                const newRooms = prevRooms.map(room => {
                    if (room.name === sourceRoom) {
                        return {
                            ...room,
                            items: room.items.filter(i => i.sku !== activeId),
                            item_count: room.item_count - 1,
                        };
                    }
                    if (room.name === destinationRoom) {
                        const movedItem = prevRooms
                            .find(r => r.name === sourceRoom)
                            ?.items.find(i => i.sku === activeId);
                        if (movedItem) {
                            return {
                                ...room,
                                items: [...room.items, { ...movedItem, location: destinationRoom }],
                                item_count: room.item_count + 1,
                            };
                        }
                    }
                    return room;
                });
                return newRooms;
            });
        },
        [findItemAndRoom]
    );

    // Handle drag end
    const handleDragEnd = useCallback(
        async (event: DragEndEvent) => {
            const { active, over } = event;
            setActiveItem(null);

            if (!over) {
                // Reset to original state
                refetch();
                return;
            }

            const activeId = active.id as string;
            const overId = over.id as string;

            // Determine the target room
            let targetRoom: string;
            if (over.data?.current?.type === 'room') {
                targetRoom = overId;
            } else {
                const { roomName } = findItemAndRoom(overId);
                targetRoom = roomName || overId;
            }

            // Find the source room
            const sourceRoom = rooms.find(r =>
                r.items.some(i => i.sku === activeId)
            )?.name;

            // If dropped in same room, just reorder (not implemented yet)
            if (sourceRoom === targetRoom) {
                return;
            }

            // Persist the move to the backend
            try {
                await moveItemToRoom(selectedSite, activeId, targetRoom);
                // Invalidate and refetch to ensure sync
                queryClient.invalidateQueries({ queryKey: ['rooms-items', selectedSite] });
            } catch (error) {
                console.error('Failed to move item:', error);
                // Revert on error
                refetch();
            }
        },
        [rooms, selectedSite, queryClient, refetch, findItemAndRoom]
    );

    const handleRoomCreated = useCallback(() => {
        refetch();
    }, [refetch]);

    // Filter out NEVER INVENTORY room for display
    const displayRooms = rooms.filter(r => r.name !== 'NEVER INVENTORY');

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <LayoutGrid className="h-6 w-6" />
                    <h1 className="text-2xl font-semibold">Room Organization</h1>
                </div>
                <div className="flex items-center gap-2">
                    <CreateRoomDialog
                        siteId={selectedSite}
                        onRoomCreated={handleRoomCreated}
                    />
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetch()}
                        disabled={isLoading}
                    >
                        <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>
            </div>

            {/* Site selector */}
            <div className="flex items-center gap-4">
                <label className="text-sm text-muted-foreground">Site:</label>
                <Select value={selectedSite} onValueChange={setSelectedSite}>
                    <SelectTrigger className="w-[250px]">
                        <SelectValue placeholder="Select a site..." />
                    </SelectTrigger>
                    <SelectContent>
                        {sitesData?.sites?.map(site => (
                            <SelectItem key={site.site_id} value={site.site_id}>
                                {site.display_name}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {/* Instructions */}
            <p className="text-sm text-muted-foreground">
                Drag and drop items between rooms to organize your inventory.
            </p>

            {/* Room Grid */}
            {isLoading ? (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
            ) : !selectedSite ? (
                <div className="flex items-center justify-center py-12 text-muted-foreground">
                    Select a site to view rooms
                </div>
            ) : (
                <DndContext
                    sensors={sensors}
                    collisionDetection={closestCorners}
                    onDragStart={handleDragStart}
                    onDragOver={handleDragOver}
                    onDragEnd={handleDragEnd}
                >
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {displayRooms.map(room => (
                            <RoomCard
                                key={room.name}
                                room={room}
                                isOver={false}
                            />
                        ))}
                    </div>

                    <DragOverlay>
                        {activeItem ? <RoomItemOverlay item={activeItem} /> : null}
                    </DragOverlay>
                </DndContext>
            )}
        </div>
    );
}
