import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
  Button,
} from 'marketmind';

export function RightPanel() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger render={<Button variant="outline">Open</Button>} />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Fund details</SheetTitle>
          <SheetDescription>
            Quick summary before opening the full report.
          </SheetDescription>
        </SheetHeader>
        <SheetFooter>
          <SheetClose render={<Button variant="ghost">Close</Button>} />
          <Button>View full report</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
