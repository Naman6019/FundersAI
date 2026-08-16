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

export function TitleInSheet() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger render={<Button variant="outline">Fund details</Button>} />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Axis Bluechip Fund</SheetTitle>
          <SheetDescription>
            Large Cap · Direct Growth · NAV ₹58.32
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
