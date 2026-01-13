import { useState } from 'react';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { createRoom, CreateRoomRequest } from '@/lib/api';

interface CreateRoomDialogProps {
    siteId: string;
    onRoomCreated: () => void;
}

const ROOM_COLORS = [
    '#60A5FA', // Blue
    '#34D399', // Green
    '#A78BFA', // Purple
    '#FBBF24', // Yellow
    '#FB923C', // Orange
    '#F87171', // Red
    '#EC4899', // Pink
    '#14B8A6', // Teal
];

export function CreateRoomDialog({ siteId, onRoomCreated }: CreateRoomDialogProps) {
    const [open, setOpen] = useState(false);
    const [name, setName] = useState('');
    const [displayName, setDisplayName] = useState('');
    const [selectedColor, setSelectedColor] = useState(ROOM_COLORS[0]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleCreate = async () => {
        if (!name.trim()) {
            setError('Room name is required');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const roomData: CreateRoomRequest = {
                name: name.trim().replace(/\s+/g, '_'),
                display_name: displayName.trim() || name.trim(),
                color: selectedColor,
            };

            await createRoom(siteId, roomData);
            setOpen(false);
            setName('');
            setDisplayName('');
            setSelectedColor(ROOM_COLORS[0]);
            onRoomCreated();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to create room';
            if (message.includes('already exists')) {
                setError('A room with this name already exists');
            } else if (message.includes('predefined')) {
                setError('Cannot use a predefined room name');
            } else {
                setError(message);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm">
                    <Plus className="h-4 w-4 mr-1" />
                    Add Room
                </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Create Custom Room</AlertDialogTitle>
                    <AlertDialogDescription>
                        Add a new room for organizing inventory items.
                    </AlertDialogDescription>
                </AlertDialogHeader>

                <div className="space-y-4 py-4">
                    <div>
                        <label className="text-sm font-medium">
                            Room Name <span className="text-red-500">*</span>
                        </label>
                        <Input
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g., Back Storage"
                            className="mt-1"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                            Spaces will be replaced with underscores
                        </p>
                    </div>

                    <div>
                        <label className="text-sm font-medium">Display Name</label>
                        <Input
                            value={displayName}
                            onChange={(e) => setDisplayName(e.target.value)}
                            placeholder="Leave empty to use room name"
                            className="mt-1"
                        />
                    </div>

                    <div>
                        <label className="text-sm font-medium">Color</label>
                        <div className="flex gap-2 mt-2 flex-wrap">
                            {ROOM_COLORS.map(color => (
                                <button
                                    key={color}
                                    type="button"
                                    onClick={() => setSelectedColor(color)}
                                    className={`w-8 h-8 rounded-full border-2 transition-all ${
                                        selectedColor === color
                                            ? 'border-foreground scale-110'
                                            : 'border-transparent hover:scale-105'
                                    }`}
                                    style={{ backgroundColor: color }}
                                    aria-label={`Select color ${color}`}
                                />
                            ))}
                        </div>
                    </div>

                    {error && (
                        <p className="text-sm text-red-500">{error}</p>
                    )}
                </div>

                <AlertDialogFooter>
                    <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleCreate} disabled={loading || !name.trim()}>
                        {loading ? 'Creating...' : 'Create Room'}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
